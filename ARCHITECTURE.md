# System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
│  - React 19 TypeScript                                          │
│  - Tailwind CSS + shadcn/ui                                    │
│  - Pages: Login, Dashboard, Ingest, Analytics                  │
│  - SWR for data fetching and caching                          │
└────────────────┬─────────────────────────────────┬─────────────┘
                 │ HTTP/REST (Token Auth)         │
                 │ CORS enabled                   │
                 ▼                                 ▼
┌──────────────────────────────────┐   ┌──────────────────────────┐
│   Django REST API (Backend)      │   │  Neon PostgreSQL         │
│  - 6 REST ViewSets               │───│  - Multi-tenant DB       │
│  - Auth token management         │   │  - RLS support           │
│  - 3 Data processors             │   │  - 5 core tables         │
│  - CORS middleware               │   │  - Audit trail           │
└──────────────────────────────────┘   └──────────────────────────┘
```

## Data Flow Architecture

### Ingestion Flow
```
User Upload (CSV/JSON)
    ↓
API Endpoint (POST /ingestion/{type}/)
    ↓
Processor (SAP/Utility/Travel)
    ├─ Parse input
    ├─ Normalize units
    ├─ Calculate emissions
    └─ Flag validation issues
    ↓
DataSource Record (tracks ingestion)
    ↓
RawEmission Records (created, status=NEW)
    ↓
AuditLog (CREATED action)
    ↓
Response to Frontend (with created records + errors)
```

### Review Flow
```
Frontend Dashboard
    ↓
List emissions with filters
    ├─ Filter by status, scope, category
    ├─ Filter by date range
    └─ Filter by has_issues
    ↓
Click to open modal
    ↓
Display record details
    ├─ Activity data
    ├─ Calculated emissions
    ├─ Validation issues (if any)
    ├─ Audit log history
    └─ Analyst notes
    ↓
Actions:
    ├─ Approve (status → APPROVED)
    ├─ Reject (status → REJECTED, requires reason)
    └─ Add notes (analyst_notes)
    ↓
AuditLog record (APPROVED/REJECTED/NOTES_ADDED)
    ↓
Record locked or available for revision
```

### Analytics Flow
```
Dashboard loads analytics page
    ↓
GET /api/analytics/summary/ (optional: with date_from/date_to filters)
    ↓
Backend aggregates:
    ├─ SUM(emissions) by scope → Scope 1, 2, 3
    ├─ SUM(emissions) by category → FUEL, ELECTRICITY, FLIGHTS, etc.
    ├─ COUNT by status → NEW, REVIEWED, APPROVED, REJECTED
    └─ COUNT records with issues
    ↓
Response with summary data
    ↓
Frontend renders:
    ├─ Summary cards (total, by scope)
    ├─ Pie chart (scope breakdown)
    ├─ Bar chart (category breakdown)
    └─ Status grid
```

## API Structure

### Authentication
```
POST /api-token-auth/
Input: { username, password }
Output: { token: "abc123..." }

All subsequent requests:
Header: Authorization: Token abc123...
```

### Ingestion Endpoints
```
POST /api/ingestion/sap/
POST /api/ingestion/utility/
POST /api/ingestion/travel/

Input: MultipartForm (file) or JSON (content)
Output: {
  status: "success" | "partial_success"
  data_source_id: uuid
  ingested_count: number
  errors: [string]
  warnings: [string]
  created_records: [RawEmission]
}
```

### Emissions Endpoints
```
GET /api/emissions/
  ?status=NEW,REVIEWED,APPROVED,REJECTED
  &scope=SCOPE_1,SCOPE_2,SCOPE_3
  &category=FUEL,ELECTRICITY,FLIGHTS
  &date_from=2024-01-01
  &date_to=2024-12-31
  &has_issues=true

GET /api/emissions/{id}/
POST /api/emissions/{id}/approve/ { notes: "..." }
POST /api/emissions/{id}/reject/ { reason: "..." }
PATCH /api/emissions/{id}/update_notes/ { notes: "..." }
```

### Analytics Endpoint
```
GET /api/analytics/summary/
  ?date_from=2024-01-01
  &date_to=2024-12-31

Output: {
  total_emissions_kg_co2e: "12345.67"
  scope_1: "5000.50"
  scope_2: "3000.25"
  scope_3: "4345.92"
  by_category: { "FUEL": "5000.50", "FLIGHTS": "3000.25", ... }
  by_status: { "NEW": 10, "APPROVED": 20, "REJECTED": 2 }
  records_with_issues: 5
}
```

## Database Schema

### Organizations
```sql
id (UUID, PK)
name (String)
email_domain (String, Unique)
created_at (DateTime)
updated_at (DateTime)
```

### UserProfile
```sql
id (UUID, PK)
user_id (FK → User)
organization_id (FK → Organization)
role (String: ADMIN, ANALYST, VIEWER)
created_at (DateTime)
updated_at (DateTime)

Index: (user_id, organization_id) UNIQUE
```

### DataSource
```sql
id (UUID, PK)
organization_id (FK → Organization)
source_type (String: SAP, UTILITY, TRAVEL)
filename (String)
ingested_at (DateTime)
ingested_by_id (FK → User, nullable)
record_count (Int)
notes (Text)

Index: (organization_id, -ingested_at)
```

### RawEmission
```sql
id (UUID, PK)
organization_id (FK → Organization)
data_source_id (FK → DataSource, nullable)
source_reference_id (String)
activity_date (Date)
activity_type (String: FUEL_DIESEL, kWh, FLIGHT_ECONOMY, etc.)
activity_value (Decimal)
activity_unit (String: L, kg, kWh, km, nights, etc.)
scope (String: SCOPE_1, SCOPE_2, SCOPE_3)
category (String: FUEL, ELECTRICITY, FLIGHTS, HOTELS, GROUND_TRANSPORT)
emission_factor (Decimal)
calculated_emissions_kg_co2e (Decimal)
status (String: NEW, REVIEWED, APPROVED, REJECTED)
reviewed_by_id (FK → User, nullable)
reviewed_at (DateTime, nullable)
rejection_reason (Text)
analyst_notes (Text)
validation_issues (JSON: [string])
created_at (DateTime)
updated_at (DateTime)

Indexes:
  (organization_id, -activity_date)
  (organization_id, status)
  (data_source_id)
```

### AuditLog
```sql
id (UUID, PK)
emission_id (FK → RawEmission)
action (String: CREATED, UPDATED, APPROVED, REJECTED, NOTES_ADDED)
changed_by_id (FK → User, nullable)
changes (JSON: {field: {old, new}})
timestamp (DateTime)
notes (Text)

Index: (emission_id, timestamp)
```

## Processor Architecture

### BaseProcessor (Abstract)
```python
class BaseProcessor(ABC):
  SOURCE_TYPE: str
  
  @abstractmethod
  def process(file_content: str, org_id: str, user) 
    → (records: [RawEmission], errors: [str], warnings: [str])
```

### SAP Processor
```
Input: CSV with columns [PO#, Material Code, Plant Code, Date, Quantity, Unit, Cost, Vendor]

Processing:
1. Parse CSV row by row
2. Extract PO#, date, quantity, UOM
3. Map material code → fuel type (DIESEL, PETROL, LPG, etc.)
4. Normalize units: convert gal→L, etc.
5. Lookup emission factor (2.68 for diesel, etc.)
6. Calculate: activity_value × emission_factor
7. Flag issues: missing values, unusual quantities
8. Create RawEmission(scope=SCOPE_1, category=FUEL)

Output: Array of RawEmission objects
```

### Utility Processor
```
Input: CSV with columns [Meter ID, Reading Date, kWh, Tariff Code]

Processing:
1. Parse CSV, group by Meter ID
2. Sort readings by date
3. Group into monthly billing periods (30-31 days)
4. For each period:
   - Sum total kWh
   - Lookup emission factor by tariff (0.40 grid avg)
   - Calculate: total_kwh × factor
   - Check for gaps (>3 days) → flag as issue
5. Create RawEmission per period (scope=SCOPE_2, category=ELECTRICITY)

Output: Array of RawEmission objects (one per billing period)
```

### Travel Processor
```
Input: JSON array with objects:
  {expense_date, expense_type, ...details}

Processing by type:
  FLIGHT:
    - Get cabin_class (default: ECONOMY)
    - Get distance (from distance_km or airport codes)
    - Apply multiplier: 1x economy, 2.5x business, 9x first
    - emission = distance × 0.16 × multiplier
    - Scope 3
  
  HOTEL:
    - Get nights
    - emission = nights × 10 kg CO2e
    - Scope 3
  
  GROUND:
    - Get distance, transport_type
    - Lookup factor: taxi=0.25, train=0.04, bus=0.08, etc.
    - emission = distance × factor
    - Scope 3

Output: Array of RawEmission objects
```

## Authentication & Authorization

### Token Flow
```
1. User logs in: POST /api-token-auth/ { username, password }
2. Backend returns token
3. Frontend stores in localStorage
4. Frontend includes in all requests: Authorization: Token {token}
5. Backend middleware validates token, extracts User
6. User.profile gives organization_id and role
```

### Permission Checks
```
IsInOrganization:
  - User must have a profile (org_id)
  - All objects must match user's org_id

IsAnalystOrHigher:
  - User role must be ANALYST or ADMIN
  - Can approve/reject records

IsAdminOrHigher:
  - User role must be ADMIN only
```

## Multi-Tenancy

### Implementation
```
1. All models have organization_id FK
2. ViewSets filter queryset by user.profile.organization
3. Serializers include organization_id
4. Frontend auth context stores user.profile.organization

Example:
  user.profile.organization_id = "org-123"
  GET /emissions/ → SELECT * WHERE organization_id = "org-123"
  POST /emissions/ → Auto-assign organization_id = "org-123"
  
  User from different org cannot access org-123's data
```

## Caching Strategy

### Frontend (SWR)
```
- GET /api/emissions/ cached with filters as key
- Auto-revalidate on tab focus
- Manual mutate() after approve/reject
- Stale-while-revalidate for faster UX
```

### Backend
```
- No explicit caching in initial version
- Database indexes on common filters:
  (organization_id, status)
  (organization_id, activity_date)
  (data_source_id)
- Consider Redis for analytics in future
```

## Error Handling

### Frontend
```
API errors caught in lib/api.ts
Returned as {error: "message"} object
Components check if 'error' in response
Display in AlertCircle badges
```

### Backend
```
Processors return (records, errors, warnings) tuple
Ingestion endpoint returns 201 with errors array
400 status if critical (no file, invalid JSON)
200 status even if partial success (to show errors)
```

## Security Considerations

1. **Authentication**: Token-based, not session-based (works with next.js/SPA)
2. **CORS**: Whitelist frontend URL in DJANGO_ALLOWED_ORIGINS
3. **HTTPS**: Required in production (set SECURE_SSL_REDIRECT)
4. **CSRF**: Disabled for API (token auth instead)
5. **SQL Injection**: Django ORM parameterizes queries
6. **Password Hashing**: Django's default bcrypt + salt
7. **RLS**: Database-level row security can be added for extra safety
