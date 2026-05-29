"""Utility functions for emissions calculations and conversions"""
from decimal import Decimal
from datetime import datetime
import re


# Emission factors (kg CO2e per unit)
EMISSION_FACTORS = {
    # Fuel (kg CO2e per liter)
    'PETROL': Decimal('2.31'),
    'DIESEL': Decimal('2.68'),
    'LPG': Decimal('1.50'),
    'NATURAL_GAS': Decimal('1.96'),  # per kg
    
    # Electricity (kg CO2e per kWh) - varies by country/grid
    'ELECTRICITY_GRID_AVG': Decimal('0.40'),  # Global average
    'ELECTRICITY_COAL': Decimal('0.82'),
    'ELECTRICITY_GAS': Decimal('0.49'),
    'ELECTRICITY_RENEWABLE': Decimal('0.04'),
    
    # Travel (kg CO2e per km)
    'FLIGHT_ECONOMY': Decimal('0.16'),  # per passenger km
    'FLIGHT_BUSINESS': Decimal('0.40'),  # 2.5x multiplier
    'FLIGHT_FIRST': Decimal('1.44'),  # 9x multiplier
    'HOTEL_PER_NIGHT': Decimal('10'),  # per night
    'CAR_PETROL': Decimal('0.21'),  # per km
    'CAR_DIESEL': Decimal('0.18'),  # per km
    'CAR_ELECTRIC': Decimal('0.05'),  # per km
    'TAXI': Decimal('0.25'),  # per km (shared)
    'BUS': Decimal('0.08'),  # per km
    'TRAIN': Decimal('0.04'),  # per km
}


def convert_fuel_liters_to_kg(liters: Decimal, fuel_type: str = 'DIESEL') -> Decimal:
    """Convert fuel liters to kg (approx density for diesel = 0.84 kg/L, petrol = 0.75 kg/L)"""
    densities = {
        'DIESEL': Decimal('0.84'),
        'PETROL': Decimal('0.75'),
        'KEROSENE': Decimal('0.80'),
    }
    density = densities.get(fuel_type.upper(), Decimal('0.80'))
    return liters * density


def convert_gallons_to_liters(gallons: Decimal) -> Decimal:
    """Convert US gallons to liters"""
    return gallons * Decimal('3.785')


def convert_miles_to_km(miles: Decimal) -> Decimal:
    """Convert miles to kilometers"""
    return miles * Decimal('1.609')


def parse_activity_value(value_str: str) -> Decimal:
    """Parse activity value from string, handling thousands separators"""
    cleaned = value_str.strip().replace(',', '').replace(' ', '')
    try:
        return Decimal(cleaned)
    except:
        return None


def parse_date(date_str: str, formats=None) -> datetime:
    """Parse various date formats"""
    if formats is None:
        formats = [
            '%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y',
            '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y',
            '%d.%m.%Y',  # German format
            '%Y-%m-%d %H:%M:%S', '%d-%m-%Y %H:%M:%S'
        ]
    
    date_str = date_str.strip()
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    return None


def extract_airport_code(text: str) -> str:
    """Extract IATA airport code from text (e.g., 'SFO', 'LHR')"""
    # Look for 3-letter uppercase code
    match = re.search(r'\b([A-Z]{3})\b', text.upper())
    return match.group(1) if match else None


def distance_between_airports(code1: str, code2: str) -> int:
    """Approximate great-circle distance between two airports (km)"""
    # Simplified approximation - in production would use actual airport coordinates
    airports = {
        'JFK': (40.6413, -73.7781),  # New York
        'LHR': (51.4700, -0.4543),   # London
        'CDG': (49.0097, 2.5479),    # Paris
        'SFO': (37.6213, -122.3790), # San Francisco
        'LAX': (33.9425, -118.4081), # Los Angeles
        'NRT': (35.7653, 140.3929),  # Tokyo
        'DXB': (25.2528, 55.3645),   # Dubai
        'SYD': (-33.9461, 151.1772), # Sydney
        'DEL': (28.5565, 77.1053),   # Delhi
        'SIN': (1.3521, 103.8198),   # Singapore
    }
    
    if code1 not in airports or code2 not in airports:
        return None
    
    # Haversine formula approximation
    from math import radians, cos, sin, asin, sqrt
    lon1, lat1 = radians(airports[code1][1]), radians(airports[code1][0])
    lon2, lat2 = radians(airports[code2][1]), radians(airports[code2][0])
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return int(km)


def validate_emissions_calculation(activity_value: Decimal, emission_factor: Decimal, calculated: Decimal) -> bool:
    """Validate that calculated emissions match activity_value * emission_factor"""
    if activity_value <= 0 or emission_factor <= 0:
        return False
    
    expected = (activity_value * emission_factor).quantize(calculated)
    tolerance = Decimal('0.01')  # 0.01 kg CO2e tolerance
    return abs(calculated - expected) <= tolerance


def flag_validation_issues(raw_dict: dict, category: str) -> list:
    """Generate list of validation issue strings for a record"""
    issues = []
    
    if not raw_dict.get('activity_value') or Decimal(str(raw_dict['activity_value'])) <= 0:
        issues.append("Missing or invalid activity value")
    
    if not raw_dict.get('activity_date'):
        issues.append("Missing activity date")
    
    if category in ['FLIGHTS', 'HOTELS'] and not raw_dict.get('source_reference_id'):
        issues.append("Missing source reference ID")
    
    # Scope/category-specific validations
    if category == 'FLIGHTS' and raw_dict.get('cabin_class') not in ['ECONOMY', 'BUSINESS', 'FIRST', None]:
        issues.append(f"Unknown cabin class: {raw_dict.get('cabin_class')}")
    
    if category == 'FLIGHTS' and (not raw_dict.get('distance_km') and 
                                   not (raw_dict.get('origin_code') and raw_dict.get('destination_code'))):
        issues.append("Missing distance or airport codes for flight")
    
    if category == 'ELECTRICITY' and Decimal(str(raw_dict.get('activity_value', 0))) > Decimal('100000'):
        issues.append("Unusually high electricity reading (>100,000 kWh) - verify data")
    
    if category == 'FUEL' and Decimal(str(raw_dict.get('activity_value', 0))) > Decimal('10000'):
        issues.append("Unusually high fuel quantity (>10,000 L/kg) - verify data")
    
    return issues
