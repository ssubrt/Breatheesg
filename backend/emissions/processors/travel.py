"""Corporate travel expense JSON processor"""
import json
from decimal import Decimal
from typing import Tuple, List, Dict, Optional
from .base import BaseProcessor
from ..models import RawEmission
from ..utils import (
    distance_between_airports, extract_airport_code, parse_date,
    EMISSION_FACTORS, flag_validation_issues
)


class TravelProcessor(BaseProcessor):
    """Processes corporate travel expense data from Navan/Concur JSON exports"""
    
    SOURCE_TYPE = 'TRAVEL'
    
    def process(self, file_content: str, organization_id: str, user) -> Tuple[list, list, list]:
        """
        Process travel expense JSON
        
        Returns:
            Tuple of (created_records, errors, warnings)
        """
        records = []
        errors = []
        warnings = []
        
        try:
            # Parse JSON
            try:
                data = json.loads(file_content)
            except json.JSONDecodeError as e:
                return records, [f"Invalid JSON: {str(e)}"], warnings
            
            # Handle both array and object with 'expenses' key
            if isinstance(data, dict):
                expenses = data.get('expenses', [])
            elif isinstance(data, list):
                expenses = data
            else:
                return records, ["JSON must be an array or object with 'expenses' array"], warnings
            
            if not expenses:
                warnings.append("No expenses found in JSON")
                return records, errors, warnings
            
            for idx, expense in enumerate(expenses):
                try:
                    emission = self._parse_expense(expense, organization_id, user, idx)
                    if emission:
                        records.append(emission)
                except ValueError as e:
                    errors.append(f"Expense {idx + 1}: {str(e)}")
                except Exception as e:
                    errors.append(f"Expense {idx + 1}: Unexpected error - {str(e)}")
        
        except Exception as e:
            return records, [f"JSON processing error: {str(e)}"], warnings
        
        return records, errors, warnings
    
    def _parse_expense(self, expense: Dict, organization_id: str, user, idx: int) -> Optional[RawEmission]:
        """Parse a single expense and create RawEmission"""
        
        expense_date = expense.get('expense_date') or expense.get('date')
        expense_type = (expense.get('expense_type') or expense.get('type', '')).upper()
        
        if not expense_date or not expense_type:
            raise ValueError("Missing expense_date or expense_type")
        
        activity_date = parse_date(str(expense_date))
        if not activity_date:
            raise ValueError(f"Invalid date: {expense_date}")
        
        source_ref = f"TRAVEL_{activity_date.isoformat()}_{idx}"
        
        # Process by type
        if expense_type in ['FLIGHT', 'AIR']:
            return self._process_flight(expense, organization_id, user, activity_date, source_ref)
        elif expense_type in ['HOTEL', 'ACCOMMODATION']:
            return self._process_hotel(expense, organization_id, user, activity_date, source_ref)
        elif expense_type in ['GROUND', 'TAXI', 'CAR', 'TRANSPORT']:
            return self._process_ground(expense, organization_id, user, activity_date, source_ref)
        else:
            raise ValueError(f"Unknown expense type: {expense_type}")
    
    def _process_flight(self, expense: Dict, organization_id: str, user, activity_date, source_ref) -> RawEmission:
        """Process flight expense"""
        
        # Get cabin class (default: economy)
        cabin_class = (expense.get('cabin_class') or expense.get('class', 'ECONOMY')).upper()
        if cabin_class not in ['ECONOMY', 'BUSINESS', 'FIRST']:
            cabin_class = 'ECONOMY'
        
        # Get distance
        distance_km = expense.get('distance_km') or expense.get('distance')
        origin = expense.get('origin_code') or expense.get('from')
        destination = expense.get('destination_code') or expense.get('to')
        
        if distance_km:
            try:
                distance_km = Decimal(str(distance_km))
            except:
                distance_km = None
        
        # Try to get distance from airport codes if not provided
        if not distance_km and origin and destination:
            origin_code = extract_airport_code(origin)
            dest_code = extract_airport_code(destination)
            if origin_code and dest_code:
                dist = distance_between_airports(origin_code, dest_code)
                if dist:
                    distance_km = Decimal(str(dist))
        
        if not distance_km or distance_km <= 0:
            raise ValueError("No distance or airport codes provided for flight")
        
        # Determine cabin class multiplier
        cabin_multipliers = {
            'ECONOMY': Decimal('1.0'),
            'BUSINESS': Decimal('2.5'),
            'FIRST': Decimal('9.0'),
        }
        multiplier = cabin_multipliers.get(cabin_class, Decimal('1.0'))
        
        # Calculate emissions
        base_factor = EMISSION_FACTORS['FLIGHT_ECONOMY']
        emission_factor = base_factor * multiplier
        calculated_emissions = distance_km * emission_factor
        
        # Validation issues
        validation_issues = flag_validation_issues({
            'activity_value': distance_km,
            'activity_date': activity_date,
            'source_reference_id': source_ref,
            'cabin_class': cabin_class,
        }, 'FLIGHTS')
        
        if not origin or not destination:
            validation_issues.append("Missing origin or destination airport information")
        
        emission = RawEmission(
            organization_id=organization_id,
            data_source=None,
            source_reference_id=source_ref,
            activity_date=activity_date,
            activity_type=f'FLIGHT_{cabin_class}',
            activity_value=distance_km,
            activity_unit='km',
            scope='SCOPE_3',
            category='FLIGHTS',
            emission_factor=emission_factor,
            calculated_emissions_kg_co2e=calculated_emissions,
            status='NEW',
            analyst_notes=f"Flight: {cabin_class} class from {origin} to {destination}",
            validation_issues=validation_issues,
        )
        
        return emission
    
    def _process_hotel(self, expense: Dict, organization_id: str, user, activity_date, source_ref) -> RawEmission:
        """Process hotel stay"""
        
        # Get nights
        nights = expense.get('nights') or expense.get('stay_duration')
        if not nights:
            raise ValueError("Missing nights or stay_duration for hotel")
        
        try:
            nights = Decimal(str(nights))
        except:
            raise ValueError(f"Invalid nights value: {nights}")
        
        if nights <= 0:
            raise ValueError("Hotel nights must be positive")
        
        # Get city/location
        city = expense.get('city') or expense.get('location', 'Unknown')
        hotel_chain = expense.get('hotel_chain') or expense.get('chain', 'Standard')
        
        # Emission factor: 10 kg CO2e per night (baseline)
        # Could be adjusted by city/chain in future
        emission_factor = EMISSION_FACTORS['HOTEL_PER_NIGHT']
        calculated_emissions = nights * emission_factor
        
        validation_issues = flag_validation_issues({
            'activity_value': nights,
            'activity_date': activity_date,
            'source_reference_id': source_ref,
        }, 'HOTELS')
        
        emission = RawEmission(
            organization_id=organization_id,
            data_source=None,
            source_reference_id=source_ref,
            activity_date=activity_date,
            activity_type='HOTEL',
            activity_value=nights,
            activity_unit='nights',
            scope='SCOPE_3',
            category='HOTELS',
            emission_factor=emission_factor,
            calculated_emissions_kg_co2e=calculated_emissions,
            status='NEW',
            analyst_notes=f"Hotel in {city} ({hotel_chain}): {nights} nights",
            validation_issues=validation_issues,
        )
        
        return emission
    
    def _process_ground(self, expense: Dict, organization_id: str, user, activity_date, source_ref) -> RawEmission:
        """Process ground transport (taxi, car, bus, train)"""
        
        transport_type = (expense.get('transport_type') or expense.get('type', 'TAXI')).upper()
        distance_km = expense.get('distance_km') or expense.get('distance')
        
        if not distance_km:
            raise ValueError("Missing distance for ground transport")
        
        try:
            distance_km = Decimal(str(distance_km))
        except:
            raise ValueError(f"Invalid distance: {distance_km}")
        
        if distance_km <= 0:
            raise ValueError("Distance must be positive")
        
        # Map to emission factor
        factor_map = {
            'TAXI': EMISSION_FACTORS.get('TAXI', Decimal('0.25')),
            'CAR': EMISSION_FACTORS.get('CAR_PETROL', Decimal('0.21')),
            'BUS': EMISSION_FACTORS.get('BUS', Decimal('0.08')),
            'TRAIN': EMISSION_FACTORS.get('TRAIN', Decimal('0.04')),
            'TRANSIT': EMISSION_FACTORS.get('BUS', Decimal('0.08')),
            'OTHER': Decimal('0.15'),
        }
        
        emission_factor = factor_map.get(transport_type, Decimal('0.15'))
        calculated_emissions = distance_km * emission_factor
        
        validation_issues = flag_validation_issues({
            'activity_value': distance_km,
            'activity_date': activity_date,
            'source_reference_id': source_ref,
        }, 'GROUND_TRANSPORT')
        
        emission = RawEmission(
            organization_id=organization_id,
            data_source=None,
            source_reference_id=source_ref,
            activity_date=activity_date,
            activity_type=f'GROUND_{transport_type}',
            activity_value=distance_km,
            activity_unit='km',
            scope='SCOPE_3',
            category='GROUND_TRANSPORT',
            emission_factor=emission_factor,
            calculated_emissions_kg_co2e=calculated_emissions,
            status='NEW',
            analyst_notes=f"Ground transport: {transport_type}",
            validation_issues=validation_issues,
        )
        
        return emission
