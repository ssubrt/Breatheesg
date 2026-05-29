"""Utility/Electricity meter CSV processor"""
import csv
import io
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Tuple, List, Dict
from .base import BaseProcessor
from ..models import RawEmission
from ..utils import parse_activity_value, parse_date, EMISSION_FACTORS, flag_validation_issues


class UtilityProcessor(BaseProcessor):
    """Processes utility meter reading CSV exports"""
    
    SOURCE_TYPE = 'UTILITY'
    EXPECTED_COLUMNS = [
        'Meter ID', 'Reading Date', 'kWh', 'Tariff Code'
    ]
    
    # Default emission factors by region/grid (kg CO2e per kWh)
    REGION_FACTORS = {
        'COAL': Decimal('0.82'),
        'GAS': Decimal('0.49'),
        'RENEWABLE': Decimal('0.04'),
        'GRID_AVG': Decimal('0.40'),
    }
    
    def process(self, file_content: str, organization_id: str, user) -> Tuple[list, list, list]:
        """
        Process utility meter CSV file
        
        Returns:
            Tuple of (created_records, errors, warnings)
        """
        records = []
        errors = []
        warnings = []
        
        try:
            csv_reader = csv.DictReader(io.StringIO(file_content))
            
            if not csv_reader.fieldnames:
                return records, ["Empty CSV file"], warnings
            
            # Validate headers
            missing_columns = set(self.EXPECTED_COLUMNS) - set(csv_reader.fieldnames or [])
            if missing_columns:
                warnings.append(f"Missing columns: {', '.join(missing_columns)}")
            
            # Group readings by meter and billing period
            meter_readings = defaultdict(list)
            row_num = 1
            
            for row in csv_reader:
                row_num += 1
                
                try:
                    meter_id = row.get('Meter ID', '').strip()
                    date_str = row.get('Reading Date', '').strip()
                    kwh_str = row.get('kWh', '').strip()
                    tariff_code = row.get('Tariff Code', '').strip()
                    
                    if not meter_id or not date_str or not kwh_str:
                        warnings.append(f"Row {row_num}: Missing meter, date, or kWh value")
                        continue
                    
                    reading_date = parse_date(date_str)
                    if not reading_date:
                        errors.append(f"Row {row_num}: Invalid date format")
                        continue
                    
                    kwh = parse_activity_value(kwh_str)
                    if kwh is None or kwh < 0:
                        errors.append(f"Row {row_num}: Invalid kWh value")
                        continue
                    
                    meter_readings[meter_id].append({
                        'date': reading_date,
                        'kwh': kwh,
                        'tariff_code': tariff_code,
                    })
                
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
            
            # Process by meter and aggregate by billing period
            for meter_id, readings in meter_readings.items():
                readings_sorted = sorted(readings, key=lambda r: r['date'])
                
                # Group into ~monthly billing periods (30-31 days)
                billing_periods = self._group_by_billing_period(readings_sorted)
                
                for period_data in billing_periods:
                    try:
                        emission = self._create_billing_period_emission(
                            period_data, meter_id, organization_id, user
                        )
                        if emission:
                            records.append(emission)
                    except ValueError as e:
                        errors.append(f"Meter {meter_id}: {str(e)}")
        
        except Exception as e:
            return records, [f"CSV parsing error: {str(e)}"], warnings
        
        return records, errors, warnings
    
    def _group_by_billing_period(self, readings: List[Dict]) -> List[Dict]:
        """Group meter readings into monthly billing periods"""
        if not readings:
            return []
        
        billing_periods = []
        current_period = []
        period_start = readings[0]['date']
        
        for reading in readings:
            days_elapsed = (reading['date'] - period_start).days
            
            # Start new period if >31 days or last reading
            if days_elapsed > 31 and current_period:
                billing_periods.append({
                    'start_date': period_start,
                    'end_date': current_period[-1]['date'],
                    'readings': current_period,
                })
                current_period = [reading]
                period_start = reading['date']
            else:
                current_period.append(reading)
        
        # Add last period
        if current_period:
            billing_periods.append({
                'start_date': period_start,
                'end_date': current_period[-1]['date'],
                'readings': current_period,
            })
        
        return billing_periods
    
    def _create_billing_period_emission(
        self, period_data: Dict, meter_id: str, organization_id: str, user
    ) -> RawEmission:
        """Create a RawEmission record for a billing period"""
        
        readings = period_data['readings']
        start_date = period_data['start_date']
        end_date = period_data['end_date']
        
        # Sum kWh for the period
        total_kwh = sum(Decimal(str(r['kwh'])) for r in readings)
        
        if total_kwh <= 0:
            raise ValueError(f"No kWh readings for meter {meter_id} in period {start_date} to {end_date}")
        
        # Determine emission factor (default: grid average)
        tariff_code = readings[0]['tariff_code'].upper() if readings[0]['tariff_code'] else 'GRID_AVG'
        emission_factor = self.REGION_FACTORS.get(tariff_code, self.REGION_FACTORS['GRID_AVG'])
        
        # Calculate emissions
        calculated_emissions = total_kwh * emission_factor
        
        # Check for gaps in readings (missing days)
        validation_issues = self._check_reading_gaps(readings)
        
        # Create record
        source_ref = f"{meter_id}_{start_date.isoformat()}"
        emission = RawEmission(
            organization_id=organization_id,
            data_source=None,  # Set by ingestion view
            source_reference_id=source_ref,
            activity_date=end_date,  # Use end of billing period as activity date
            activity_type='ELECTRICITY',
            activity_value=total_kwh,
            activity_unit='kWh',
            scope='SCOPE_2',
            category='ELECTRICITY',
            emission_factor=emission_factor,
            calculated_emissions_kg_co2e=calculated_emissions,
            status='NEW',
            analyst_notes=f"Meter {meter_id}: {len(readings)} readings from {start_date} to {end_date}",
            validation_issues=validation_issues,
        )
        
        return emission
    
    def _check_reading_gaps(self, readings: List[Dict]) -> List[str]:
        """Check for gaps in meter readings (missing days)"""
        issues = []
        
        if len(readings) < 2:
            issues.append("Only one reading for period - cannot verify consistency")
            return issues
        
        readings_sorted = sorted(readings, key=lambda r: r['date'])
        
        # Check for gaps > 3 days
        for i in range(len(readings_sorted) - 1):
            current_date = readings_sorted[i]['date']
            next_date = readings_sorted[i + 1]['date']
            gap = (next_date - current_date).days
            
            if gap > 3:
                issues.append(f"Gap in readings: {gap} days between {current_date} and {next_date}")
        
        return issues
