from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date

from emissions.models import Organization, RawEmission, DataSource
from emissions.processors.sap import SAPProcessor
from emissions.processors.utility import UtilityProcessor
from emissions.processors.travel import TravelProcessor


class EmissionsProcessorTests(TestCase):
    """Test suite for emissions ingestion processors and validation rules"""

    def setUp(self):
        # Set up organization and test user
        self.organization = Organization.objects.create(
            name="Test Enterprise Corp",
            email_domain="testenterprise.com"
        )
        self.user = User.objects.create_user(
            username="analyst@testenterprise.com",
            email="analyst@testenterprise.com",
            password="testpassword"
        )
        # Create user profile role
        from emissions.models import UserProfile
        self.profile = UserProfile.objects.create(
            user=self.user,
            organization=self.organization,
            role="ANALYST"
        )

    def test_sap_processor_standard_headers(self):
        """Test SAP processor with standard English headers"""
        csv_content = (
            "PO#,Material Code,Plant Code,Date,Quantity,Unit of Measure,Cost,Vendor\n"
            "PO-100,FUEL-DIESEL-100,PLANT-A,2024-01-15,100,L,250,Shell"
        )
        
        processor = SAPProcessor()
        records, errors, warnings = processor.process(
            csv_content, str(self.organization.id), self.user
        )
        
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(records), 1)
        
        record = records[0]
        self.assertEqual(record.source_reference_id, "PO-100")
        self.assertEqual(record.activity_type, "FUEL_DIESEL")
        # 100 liters of diesel at 0.84 kg/L density = 84 kg
        self.assertEqual(record.activity_value, Decimal("84.00")) 
        self.assertEqual(record.activity_unit, "kg")
        self.assertEqual(record.scope, "SCOPE_1")
        self.assertEqual(record.category, "FUEL")
        # Check if plant lookup was populated in analyst notes
        self.assertIn("Munich Headquarters", record.analyst_notes)
        self.assertIn("DE", record.analyst_notes)

    def test_sap_processor_german_headers_and_date(self):
        """Test SAP processor with German column headers and German date format"""
        csv_content = (
            "Bestellnummer,Materialnummer,Werk,Datum,Menge,Einheit,Kosten,Lieferant\n"
            "PO-101,FUEL-PETROL-50,PLANT-C,28.02.2024,50,GAL,180,BP"
        )
        
        processor = SAPProcessor()
        records, errors, warnings = processor.process(
            csv_content, str(self.organization.id), self.user
        )
        
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(records), 1)
        
        record = records[0]
        self.assertEqual(record.source_reference_id, "PO-101")
        self.assertEqual(record.activity_type, "FUEL_PETROL")
        # 50 gallons to liters = 50 * 3.785 = 189.25 L
        # Since it is fuel petrol, it converts L to kg: 189.25 * 0.75 density = 141.9375 kg
        self.assertAlmostEqual(record.activity_value, Decimal("141.9375"), places=4)
        self.assertEqual(record.activity_unit, "kg")
        self.assertEqual(record.activity_date, date(2024, 2, 28))
        self.assertIn("Bangalore Office", record.analyst_notes)
        self.assertIn("IN", record.analyst_notes)

    def test_utility_processor_billing_periods_and_gaps(self):
        """Test Utility processor grouping readings into billing periods and flagging gaps"""
        # Meter reading dataset with a gap > 3 days between Jan 8 and Jan 15 (7 day gap)
        csv_content = (
            "Meter ID,Reading Date,kWh,Tariff Code\n"
            "METER-01,2024-01-01,100,GRID_AVG\n"
            "METER-01,2024-01-08,120,GRID_AVG\n"
            "METER-01,2024-01-15,110,GRID_AVG\n"
            "METER-01,2024-01-22,130,GRID_AVG\n"
            "METER-01,2024-01-31,115,GRID_AVG"
        )
        
        processor = UtilityProcessor()
        records, errors, warnings = processor.process(
            csv_content, str(self.organization.id), self.user
        )
        
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(records), 1)
        
        record = records[0]
        self.assertEqual(record.source_reference_id, "METER-01_2024-01-01")
        self.assertEqual(record.scope, "SCOPE_2")
        self.assertEqual(record.category, "ELECTRICITY")
        # Sum of kWh = 100+120+110+130+115 = 575 kWh
        self.assertEqual(record.activity_value, Decimal("575.0"))
        self.assertEqual(record.activity_unit, "kWh")
        
        # Check validation issues (should flag reading gaps > 3 days)
        self.assertTrue(len(record.validation_issues) > 0)
        self.assertTrue(any("Gap in readings" in issue for issue in record.validation_issues))

    def test_travel_processor_flights(self):
        """Test travel processor flight emission calculations, cabin multipliers, and airport codes"""
        expense_data = [
            {
                "expense_date": "2024-01-15",
                "expense_type": "FLIGHT",
                "origin_code": "SFO",
                "destination_code": "LHR",
                "cabin_class": "BUSINESS"
            },
            {
                "expense_date": "2024-01-16",
                "expense_type": "HOTEL",
                "nights": 3,
                "city": "London"
            }
        ]
        
        import json
        file_content = json.dumps(expense_data)
        
        processor = TravelProcessor()
        records, errors, warnings = processor.process(
            file_content, str(self.organization.id), self.user
        )
        
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(records), 2)
        
        # Flight checks
        flight = [r for r in records if r.category == "FLIGHTS"][0]
        self.assertEqual(flight.scope, "SCOPE_3")
        # Approximate SFO-LHR distance from our dictionary is 8612 km (Haversine lookup)
        # Let's verify it parsed the airport codes and estimated a positive distance
        self.assertTrue(flight.activity_value > 0)
        self.assertEqual(flight.activity_unit, "km")
        
        # Business cabin class multiplier = 2.5x base factor of 0.16 = 0.40 kg CO2e per km
        self.assertEqual(flight.emission_factor, Decimal("0.40"))
        self.assertEqual(flight.calculated_emissions_kg_co2e, flight.activity_value * Decimal("0.40"))
        
        # Hotel checks
        hotel = [r for r in records if r.category == "HOTELS"][0]
        self.assertEqual(hotel.scope, "SCOPE_3")
        self.assertEqual(hotel.activity_value, Decimal("3")) # 3 nights
        self.assertEqual(hotel.activity_unit, "nights")
        self.assertEqual(hotel.calculated_emissions_kg_co2e, Decimal("30")) # 3 nights * 10 kg/night
