"""SAP fuel and procurement CSV processor"""
import csv
import io
from decimal import Decimal
from datetime import datetime
from typing import Tuple, List, Dict
from .base import BaseProcessor
from ..models import RawEmission, SCOPE_CHOICES, EMISSION_CATEGORY_CHOICES
from ..utils import (
    parse_activity_value, parse_date, convert_fuel_liters_to_kg,
    convert_gallons_to_liters, EMISSION_FACTORS, flag_validation_issues
)


class SAPProcessor(BaseProcessor):
    """Processes SAP fuel and procurement CSV exports"""
    
    SOURCE_TYPE = 'SAP'
    EXPECTED_COLUMNS = [
        'PO#', 'Material Code', 'Plant Code', 'Date', 
        'Quantity', 'Unit of Measure', 'Cost', 'Vendor'
    ]
    
    # Translation map for German headers or alternate English headers
    HEADER_MAPPING = {
        # PO# equivalents
        'PO#': 'PO#',
        'PO': 'PO#',
        'PURCHASE ORDER': 'PO#',
        'BESTELLNUMMER': 'PO#',
        'EINKAUFSBELEG': 'PO#',
        
        # Material Code equivalents
        'MATERIAL CODE': 'Material Code',
        'MATERIAL': 'Material Code',
        'MATERIALNUMMER': 'Material Code',
        'ARTIKELNUMMER': 'Material Code',
        
        # Plant Code equivalents
        'PLANT CODE': 'Plant Code',
        'PLANT': 'Plant Code',
        'WERK': 'Plant Code',
        'BETRIEB': 'Plant Code',
        
        # Date equivalents
        'DATE': 'Date',
        'DATUM': 'Date',
        'BUCHUNGSDATUM': 'Date',
        
        # Quantity equivalents
        'QUANTITY': 'Quantity',
        'QTY': 'Quantity',
        'MENGE': 'Quantity',
        
        # Unit of Measure equivalents
        'UNIT OF MEASURE': 'Unit of Measure',
        'UOM': 'Unit of Measure',
        'UNIT': 'Unit of Measure',
        'EINHEIT': 'Unit of Measure',
        
        # Cost equivalents
        'COST': 'Cost',
        'NETTO-WERT': 'Cost',
        'PREIS': 'Cost',
        'BETRAG': 'Cost',
        
        # Vendor equivalents
        'VENDOR': 'Vendor',
        'SUPPLIER': 'Vendor',
        'LIEFERANT': 'Vendor',
        'KREDITOR': 'Vendor',
    }
    
    # Plant code geographic location lookup for emissions boundary analysis
    PLANT_LOOKUP = {
        'PLANT-A': {'name': 'Munich Headquarters', 'country': 'DE', 'region': 'Europe'},
        'PLANT-B': {'name': 'Austin Data Center', 'country': 'US', 'region': 'Americas'},
        'PLANT-C': {'name': 'Bangalore Office', 'country': 'IN', 'region': 'Asia-Pacific'},
    }
    
    # Material code patterns to emissions category mapping
    MATERIAL_PATTERNS = {
        'FUEL': ['DIESEL', 'PETROL', 'GAS', 'LPG', 'FUEL'],
        'OTHER': ['MISC', 'SUPPLY', 'PART'],
    }
    
    def process(self, file_content: str, organization_id: str, user) -> Tuple[list, list, list]:
        """
        Process SAP CSV file
        
        Returns:
            Tuple of (created_records, errors, warnings)
        """
        records = []
        errors = []
        warnings = []
        
        try:
            # Parse CSV
            csv_reader = csv.DictReader(io.StringIO(file_content))
            
            if not csv_reader.fieldnames:
                return records, ["Empty CSV file"], warnings
            
            # Standardize and translate column headers
            raw_fieldnames = csv_reader.fieldnames or []
            translated_fieldnames = []
            translation_map = {}
            
            for header in raw_fieldnames:
                clean_header = header.strip().upper()
                standard_header = self.HEADER_MAPPING.get(clean_header)
                if standard_header:
                    translation_map[header] = standard_header
                    translated_fieldnames.append(standard_header)
                else:
                    translation_map[header] = header
                    translated_fieldnames.append(header)
            
            # Validate headers against translated headers
            missing_columns = set(self.EXPECTED_COLUMNS) - set(translated_fieldnames)
            if missing_columns:
                warnings.append(f"Missing columns: {', '.join(missing_columns)}")
            
            row_num = 1
            for row in csv_reader:
                row_num += 1
                
                # Map keys to standard English headers
                translated_row = {translation_map.get(k, k): v for k, v in row.items() if k is not None}
                
                try:
                    emission = self._parse_sap_row(translated_row, organization_id, user)
                    if emission:
                        records.append(emission)
                except ValueError as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                except Exception as e:
                    errors.append(f"Row {row_num}: Unexpected error - {str(e)}")
        
        except Exception as e:
            return records, [f"CSV parsing error: {str(e)}"], warnings
        
        return records, errors, warnings
    
    def _parse_sap_row(self, row: Dict, organization_id: str, user) -> RawEmission:
        """Parse a single SAP row and create RawEmission"""
        
        # Extract fields
        po_num = row.get('PO#', '').strip()
        material_code = row.get('Material Code', '').strip()
        plant_code = row.get('Plant Code', '').strip()
        date_str = row.get('Date', '').strip()
        quantity_str = row.get('Quantity', '').strip()
        uom = row.get('Unit of Measure', '').strip()
        vendor = row.get('Vendor', '').strip()
        
        # Validate required fields
        if not po_num or not date_str or not quantity_str:
            raise ValueError("Missing PO#, Date, or Quantity")
        
        # Parse date
        activity_date = parse_date(date_str)
        if not activity_date:
            raise ValueError(f"Invalid date format: {date_str}")
        
        # Parse quantity
        activity_value = parse_activity_value(quantity_str)
        if activity_value is None:
            raise ValueError(f"Invalid quantity: {quantity_str}")
        
        # Determine category based on material code
        category = self._determine_category(material_code)
        
        # Normalize units and value
        activity_unit = self._normalize_unit(uom)
        if activity_unit == 'gal':
            activity_value = convert_gallons_to_liters(activity_value)
            activity_unit = 'L'
            
        if activity_unit == 'L' and category == 'FUEL':
            # For fuel, convert liters to kg CO2e
            fuel_type = self._determine_fuel_type(material_code)
            activity_kg = convert_fuel_liters_to_kg(activity_value, fuel_type)
            activity_unit = 'kg'
            activity_value = activity_kg
        
        # Get emission factor
        fuel_type = self._determine_fuel_type(material_code)
        emission_factor = EMISSION_FACTORS.get(fuel_type, EMISSION_FACTORS['DIESEL'])
        
        # Calculate emissions
        calculated_emissions = activity_value * emission_factor
        
        # Validation issues
        validation_issues = flag_validation_issues({
            'activity_value': activity_value,
            'activity_date': activity_date,
            'source_reference_id': po_num,
        }, category)
        
        # Look up plant geographic metadata
        plant_info = self.PLANT_LOOKUP.get(plant_code.upper())
        plant_meta = ""
        if plant_info:
            plant_meta = f" [Plant: {plant_info['name']} ({plant_info['region']}/{plant_info['country']})]"
        else:
            plant_meta = f" [Plant: Unknown ({plant_code})]"
            
        # Create record
        emission = RawEmission(
            organization_id=organization_id,
            data_source=None,  # Set by ingestion view
            source_reference_id=po_num,
            activity_date=activity_date,
            activity_type=f'FUEL_{fuel_type}',
            activity_value=activity_value,
            activity_unit=activity_unit,
            scope='SCOPE_1',
            category=category,
            emission_factor=emission_factor,
            calculated_emissions_kg_co2e=calculated_emissions,
            status='NEW',
            analyst_notes=f"PO: {po_num}, Material: {material_code}{plant_meta}, Vendor: {vendor}",
            validation_issues=validation_issues,
        )
        
        return emission
    
    def _determine_category(self, material_code: str) -> str:
        """Determine emission category from material code"""
        code_upper = material_code.upper()
        for keyword in self.MATERIAL_PATTERNS.get('FUEL', []):
            if keyword in code_upper:
                return 'FUEL'
        return 'OTHER'
    
    def _determine_fuel_type(self, material_code: str) -> str:
        """Determine fuel type from material code"""
        code_upper = material_code.upper()
        if 'DIESEL' in code_upper:
            return 'DIESEL'
        elif 'PETROL' in code_upper or 'GASOLINE' in code_upper:
            return 'PETROL'
        elif 'LPG' in code_upper:
            return 'LPG'
        elif 'GAS' in code_upper:
            return 'NATURAL_GAS'
        return 'DIESEL'  # Default
    
    def _normalize_unit(self, uom: str) -> str:
        """Normalize unit of measure"""
        uom_upper = uom.strip().upper()
        
        # Check exact matches first to prevent substring collisions (e.g., 'GAL' matching 'L')
        if uom_upper in ['GAL', 'GALLON', 'GALLONS', 'G']:
            return 'gal'
        elif uom_upper in ['L', 'LITER', 'LITERS', 'LITRE', 'LITRES']:
            return 'L'
        elif uom_upper in ['KG', 'KILOGRAM', 'KILOGRAMS']:
            return 'kg'
        elif uom_upper in ['M3', 'CUBIC METER', 'CUBIC METERS']:
            return 'm3'
        
        # Fallbacks with safe precedence
        if 'GAL' in uom_upper or 'GALLON' in uom_upper:
            return 'gal'
        elif 'L' in uom_upper or 'LITER' in uom_upper or 'LITRE' in uom_upper:
            return 'L'
        elif 'KG' in uom_upper or 'KILOGRAM' in uom_upper:
            return 'kg'
        elif 'M3' in uom_upper:
            return 'm3'
        
        return uom  # Return as-is if not recognized
