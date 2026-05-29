# Real-World Data Sources & Ingestion Research

This document outlines the real-world formatting research, sample data decisions, and production failure modes for our three data sources.

---

## 1. SAP Fuel & Procurement Data

### A. Real-World Format Research
In enterprise environments, SAP fuel and procurement data is extracted in one of three ways:
1.  **Direct Database/BAPI Access**: Querying standard tables like `EKPO` (Purchasing Document Item) or `MSEG` (Document Segment: Material) using BAPIs (Business Application Programming Interfaces).
2.  **IDocs (Intermediate Documents)**: Hierarchical structures (usually XML or flat files) transferred asynchronously for EDI (Electronic Data Interchange), containing segments like `E1EDK01` (Header) and `E1EDP01` (Item).
3.  **Flat CSV/Excel Exports**: Standard transaction reports (such as `ME2N` for Purchase Orders or `MB51` for Material Documents) exported directly from the SAP GUI.

**Our Choice & Justification**: We chose to handle **Flat CSV Exports**. This represents the path of least resistance for onboarding enterprise clients, avoiding complex SAP system integrations, custom ABAP code development, VPN configurations, and high licensing costs.

### B. Real-World Complexities Resolved
*   **Language & Headers**: SAP configurations in European offices frequently output German column headers (e.g. `Bestellnummer` for PO#, `Werk` for Plant Code, `Menge` for Quantity). Our engine maps these variants to standard English targets.
*   **Plant Code Lookup**: Plant codes (e.g., `PLANT-A`) are abstract internal identifiers. Our system lookup matches these to physical locations (e.g., Munich, Germany) to track geographic emissions boundaries.
*   **Unit Mismatches**: Procurement teams buy fuel in mixed units (Liters, US Gallons, Kilograms). The processor normalizes these values using density metrics (e.g. `0.84 kg/L` for Diesel) into standardized mass (`kg`).

### C. Sample Data Design & Rationale
Our sample dataset ([`sap_example.csv`](file:///Users/subratgangwar/Documents/Subrat/VsCode/Breatheesg/next-js-e2-e-app/sample-data/sap_example.csv)) reflects:
*   A mixture of fuel purchase orders (`FUEL-DIESEL-100`, `FUEL-PETROL-50`) and miscellaneous procurement supplies (`SUPPLIES-MISC`).
*   Mixed volume/mass units (`L`, `kg`).
*   Diverse plant locations (`PLANT-A`, `PLANT-B`, `PLANT-C`) representing multi-facility operations.

### D. Production Failure Modes (What Would Break?)
*   **Custom Z-Fields**: SAP instances are heavily customized. Clients often map POs to custom fields (e.g. `ZZ_FUEL_QTY`), breaking static header parsers.
*   **German Abbreviated Units**: Units of measure may be abbreviated in German (e.g., `ST` for *Stück* instead of `pcs` / `units`).
*   **Split Account Assignments**: A single PO item might be split between multiple plant cost centers, necessitating fractional emissions allocations.

---

## 2. Utility Data (Electricity)

### A. Real-World Format Research
Facilities teams collect electricity data through:
1.  **PDF/Paper Invoices**: Scraping utility bills or manually entering values.
2.  **Utility Portal Exports**: Automated or manual CSV downloads of interval data (hourly/daily) or monthly totals.
3.  **Green Button API**: A standardized XML/JSON data standard adopted by utilities for sharing consumption data.

**Our Choice & Justification**: We chose **Utility Portal CSV exports of interval/daily readings**. This represents a realistic compromise since API billing integrations are highly fragmented across regional grids, while PDF scraping is brittle and prone to transcription errors.

### B. Real-World Complexities Resolved
*   **Billing Period Mismatch**: Meter readings rarely align with calendar months (e.g. readings on Dec 12, Dec 25, Jan 14). The processor groups readings into dynamic ~30-day billing periods to construct accurate emissions footprints.
*   **Gaps in Readings**: Broken meters or billing errors create gaps in history. Our engine checks date spacing and raises warnings if a gap exceeds 3 days, alerting the analyst to review.
*   **Tariff structures**: Clean electricity tariffs (renewables) have significantly lower factors than standard coal-heavy grids. The processor uses tariff codes to apply custom emission factors.

### C. Sample Data Design & Rationale
Our sample dataset ([`utility_example.csv`](file:///Users/subratgangwar/Documents/Subrat/VsCode/Breatheesg/next-js-e2-e-app/sample-data/utility_example.csv)) simulates:
*   Daily/weekly meter readings for two separate meters (`METER-001`, `METER-002`).
*   A simulated reading gap in February for `METER-001` (to test validation warning flags).

### D. Production Failure Modes (What Would Break?)
*   **Net-Metering & Generation**: Sites with solar panels feed electricity back, producing negative kWh values. If the engine doesn't distinguish consumption from generation, it may output faulty negative emissions.
*   **Meter Replacements**: When a physical meter is swapped, the cumulative reading resets, creating sudden drop-offs that standard calculators would flag as errors.

---

## 3. Corporate Travel (Flights, Hotels, Ground Transport)

### A. Real-World Format Research
Platforms like Navan, Concur, or TripActions expose travel data via:
1.  **Scheduled SFTP Exports**: Nightly JSON or CSV file drops containing expense details.
2.  **REST APIs**: Syncing trips via Webhooks or poller endpoints.

**Our Choice & Justification**: We chose **SFTP-style JSON payloads**. It fits the typical data engineering pipelines of enterprise travel tracking, allowing structured nested objects (flight segments, lodging details) to be parsed programmatically.

### B. Real-World Complexities Resolved
*   **Missing Flight Distances**: Expense logs often omit flight distances. Our engine extracts IATA airport codes (`SFO`, `LHR`, etc.) and computes distances using a built-in coordinates database and the Haversine formula.
*   **Cabin Class Multipliers**: Business class and first class seats occupy more cabin footprint and weight, carrying higher footprints. The processor applies GHG Protocol multipliers (1.0x Economy, 2.5x Business, 9.0x First Class).
*   **Hotel Nightly Baselines**: Hotel stays calculate footprints based on room-nights rather than flight distance, normalizing hotel data into standard nightly emissions.

### C. Sample Data Design & Rationale
Our sample dataset ([`travel_example.json`](file:///Users/subratgangwar/Documents/Subrat/VsCode/Breatheesg/next-js-e2-e-app/sample-data/travel_example.json)) represents:
*   A multi-segment travel itinerary (Flights with varying cabin classes, hotel stays, and ground transportation like taxi and train).
*   Missing distance metrics for certain flights (forcing airport code geocoding fallback).

### D. Production Failure Modes (What Would Break?)
*   **Multi-Leg & Round-Trip Bundles**: A single booking may group three flights (SFO → JFK → LHR → SFO) as a single expense, making simple origin-destination geocoding lookups fail.
*   **Unknown Airport Codes**: Small regional airports missing from the coordinate database will cause distance lookups to throw errors.
*   **Cancelled/Refunded Bookings**: Travel plans change. If the export doesn't link refunds to original bookings, the system will double-count cancelled travel.
