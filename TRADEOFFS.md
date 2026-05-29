# Architectural Tradeoffs

This document outlines three deliberate scope exclusions made during the design and build of this prototype, explaining the rationale and tradeoffs for each decision.

---

## 1. Batch File Uploads Instead of Real-time API Integrations

### What We Did Not Build
We did not implement real-time API integrations (e.g. connecting to SAP OData endpoints, Navan REST APIs, or Green Button utility database webhooks) for live data streaming. Instead, the ingestion engine relies on manual batch uploads (CSV and JSON) or copy-pasting of raw logs.

### Rationale & Tradeoffs
*   **Integration Overhead**: Real-world API integrations require OAuth credentials, VPN tunnels, static IP whitelisting, and staging sandbox environments. For a 4-day prototype, establishing these integrations is impractical without access to client instances.
*   **Operational Alignment**: Enterprise sustainability metrics are rarely processed in real-time. Compliance reports are compiled on monthly, quarterly, or annual schedules. Batch exports from ERP (SAP) and corporate travel tools are standard practice for sustainability managers today.
*   **Flexibility**: Accepting CSV and JSON exports gives the client team maximum flexibility without coupling the ingestion platform to specific API schemas, which frequently change.

---

## 2. Static Airport Coordinates Database for Distance Calculations

### What We Did Not Build
We did not import a full global database of 10,000+ airport IATA codes (e.g., OpenFlights) or integrate a third-party geocoding API (e.g., Google Maps, GeoNames) to calculate flight distances on the fly. Instead, we hardcoded coordinates for 10 major international transit hubs (SFO, LHR, JFK, LAX, NRT, CDG, DXB, SYD, SIN, DEL) in [`backend/emissions/utils.py`](file:///Users/subratgangwar/Documents/Subrat/VsCode/Breatheesg/next-js-e2-e-app/backend/emissions/utils.py) to run a local Haversine formula approximation.

### Rationale & Tradeoffs
*   **Data Bloat & Latency**: Storing a massive geographic database inside the Django relational schema introduces database bloat and increases migration complexity.
*   **External API Risk**: Calling third-party geocoding APIs introduces network latency, rate-limiting constraints, billing risks, and API key management overhead.
*   **Prototype Validity**: Demonstrating the distance lookup workflow using major international airports is sufficient to prove the viability of the geocoding fallback pattern. In a production build, this would be replaced with a cached lookup using a lightweight local key-value store (e.g., Redis) populated from a complete IATA dataset.

---

## 3. Gap Alerting Over Automated Data Estimation (Backfilling)

### What We Did Not Build
We did not implement automated data estimation algorithms (such as linear interpolation or average daily baselining) to automatically fill gaps in utility readings or correct anomalies. Instead, we flag issues (such as utility reading gaps >3 days or unusually high fuel purchases) as warnings on the dashboard.

### Rationale & Tradeoffs
*   **Audit Trail Compliance**: In carbon accounting, compliance audits require strict lineage tracking. Having the system auto-calculate and inject "fake" historical estimates directly into the database without manual analyst oversight undermines audit transparency.
*   **Non-standard Estimation Models**: Different standards (e.g., GHG Protocol, DEFRA, US EPA) require different baselining and interpolation methodologies. Auto-backfilling data could violate a client's specific accounting standards.
*   **Analyst Control**: By surfacing gaps as validation issues, we keep the analyst in control. They can manually verify the records, write notes to document why a gap exists (e.g., "Facility was closed for maintenance"), and approve or reject the record with full accountability.
