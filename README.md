# Breathe ESG - Data Ingestion Platform

Enterprise emissions data ingestion, normalization, and review system. Ingest emissions data from SAP, utility providers, and corporate travel platforms, then review and approve records with comprehensive audit trails.

## Project Structure

```
/
├── backend/          # Django REST API
│   ├── config/       # Django settings and URL routing
│   ├── emissions/    # Main app with models, views, serializers
│   │   ├── models.py # Database models
│   │   ├── views.py  # DRF ViewSets and API endpoints
│   │   ├── serializers.py # Data serialization
│   │   ├── processors/ # SAP, Utility, Travel data processors
│   │   └── urls.py   # API routing
│   ├── manage.py     # Django CLI
│   └── requirements.txt
│
├── frontend/         # Next.js + React TypeScript frontend
│   ├── app/          # App Router pages
│   │   ├── login/    # Authentication
│   │   └── (protected)/ # Protected routes with sidebar
│   │       ├── dashboard/ # Review dashboard
│   │       ├── ingest/    # Data ingestion hub
│   │       └── analytics/ # Emissions summary
│   ├── components/   # Reusable UI components
│   ├── lib/          # Utilities, types, API client
│   └── package.json
│
└── README.md         # This file
```

## Technology Stack

### Backend
- **Framework**: Django 6.0 + Django REST Framework
- **Database**: Neon PostgreSQL (serverless)
- **Authentication**: Token-based auth
- **Deployment**: Railway, Render, or similar

### Frontend
- **Framework**: Next.js 16 + React 19 + TypeScript
- **Styling**: Tailwind CSS 4 + shadcn/ui
- **Data Fetching**: SWR
- **Deployment**: Vercel

## Setup Instructions

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your DATABASE_URL from Neon

# Run migrations
python manage.py migrate

# Create superuser (optional, for admin panel)
python manage.py createsuperuser

# Start development server
python manage.py runserver 0.0.0.0:8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install  # or npm install / yarn install

# Copy environment template
cp .env.example .env.local
# Edit with your API URL (default: http://localhost:8000/api)

# Start development server
pnpm dev
```

Visit `http://localhost:3000` and use demo credentials to log in.

## Database Setup

### Using Neon PostgreSQL

1. Create a Neon project at [neon.tech](https://neon.tech)
2. Copy your connection string: `postgresql://user:password@host/dbname`
3. Add to backend `.env`:
   ```
   DATABASE_URL=postgresql://user:password@host/dbname
   ```
4. Run migrations:
   ```bash
   python manage.py migrate
   ```

## API Documentation

### Authentication
```
POST /api/api-token-auth/
{
  "username": "user@example.com",
  "password": "password"
}
Response: { "token": "abc123..." }
```

Include token in headers: `Authorization: Token abc123...`

### Data Ingestion

**SAP Fuel/Procurement:**
```
POST /api/ingestion/sap/
Content-Type: multipart/form-data
file: [CSV file]
```

**Utility Meters:**
```
POST /api/ingestion/utility/
Content-Type: multipart/form-data
file: [CSV file]
```

**Travel Expenses:**
```
POST /api/ingestion/travel/
Content-Type: application/json
{
  "content": "[{...}]"  // JSON array of expenses
}
```

### Emissions Records
```
GET /api/emissions/                           # List all
GET /api/emissions/{id}/                      # Get one
POST /api/emissions/{id}/approve/             # Approve
POST /api/emissions/{id}/reject/              # Reject with reason
PATCH /api/emissions/{id}/update_notes/       # Add notes
```

### Analytics
```
GET /api/analytics/summary/                   # Scope breakdown, totals
GET /api/analytics/summary/?date_from=2024-01-01&date_to=2024-12-31
```

## Data Models

### Organization
Multi-tenant container for users and emissions data.

### UserProfile
Links Django User to Organization with role (ADMIN/ANALYST/VIEWER).

### DataSource
Tracks each ingestion event (file, timestamp, user, record count).

### RawEmission
Normalized emissions record with:
- Activity data (date, value, unit)
- Classification (scope, category)
- Calculation (emission factor, calculated emissions)
- Review status (NEW → REVIEWED → APPROVED/REJECTED)
- Validation issues (array of strings)

### AuditLog
Immutable log of all changes with user, action, and changes dict.

## Data Processors

### SAP Processor
- Accepts CSV with columns: PO#, Material Code, Plant Code, Date, Quantity, Unit of Measure, Cost, Vendor
- Normalizes units (L, gal, kg, m³) to kg
- Maps material codes to fuel types
- Classifies as Scope 1 (Direct Fuel)
- Flags unusual quantities and missing values

### Utility Processor
- Accepts CSV with columns: Meter ID, Reading Date, kWh, Tariff Code
- Groups readings into monthly billing periods
- Sums kWh per period
- Applies region-based emission factors
- Flags gaps in readings (>3 days)
- Classifies as Scope 2 (Indirect Energy)

### Travel Processor
- Accepts JSON array of expense records
- Handles flights (with cabin class multipliers), hotels, ground transport
- Flights: 0.16 kg CO₂e/km × cabin multiplier (1x economy, 2.5x business, 9x first)
- Hotels: 10 kg CO₂e/night
- Ground: varies by transport type (taxi, bus, train, etc.)
- Classifies as Scope 3 (Other Indirect)

## Sample Data

See `/sample-data/` directory for example files:
- `sap_example.csv` - SAP procurement data
- `utility_example.csv` - Meter readings
- `travel_example.json` - Travel expenses

## Emission Factors

### Default Values (kg CO₂e)
- Diesel: 2.68 per liter
- Petrol: 2.31 per liter
- Electricity (avg): 0.40 per kWh
- Flight (economy): 0.16 per km
- Hotel: 10 per night
- Taxi: 0.25 per km
- Bus: 0.08 per km
- Train: 0.04 per km

Customize in `backend/emissions/utils.py` EMISSION_FACTORS dict.

## Authentication & Authorization

### Roles
- **ADMIN**: Full access, can approve/reject all records
- **ANALYST**: Can upload data, review and approve records
- **VIEWER**: Read-only access to dashboard and analytics

### Multi-Tenancy
All data is isolated by organization_id. Users only see their org's data. RLS (Row-Level Security) can be enforced at the database level.

## Deployment

### Backend (Django)
1. Set environment variables (DATABASE_URL, SECRET_KEY, ALLOWED_HOSTS, DEBUG=False)
2. Run migrations: `python manage.py migrate`
3. Collect static files: `python manage.py collectstatic`
4. Deploy to Railway, Render, Fly.io, or similar

### Frontend (Next.js)
1. Build: `pnpm build`
2. Deploy to Vercel or similar
3. Set environment variable: `NEXT_PUBLIC_API_URL=https://api.example.com/api`

## Troubleshooting

### Database Connection Error
- Verify DATABASE_URL is correct
- Check if PostgreSQL is running
- Ensure psycopg2 is installed: `pip install psycopg2-binary`

### CORS Errors
- Update CORS_ALLOWED_ORIGINS in backend/config/settings.py
- Frontend URL must be in the whitelist

### CSV Upload Fails
- Verify file is valid CSV format
- Check column headers match expected format
- Look at error messages in response for specific issues

### Missing Emissions Records
- Check organization_id matches user's org
- Verify user has proper token in Authorization header
- Check status filters in query params

## Support

For issues or questions, refer to the documentation files:
- [MODEL.md](file:///Users/subratgangwar/Documents/Subrat/VsCode/Breatheesg/next-js-e2-e-app/MODEL.md) - Database schema, multi-tenancy, unit normalization, and audit trails
- [DECISIONS.md](file:///Users/subratgangwar/Documents/Subrat/VsCode/Breatheesg/next-js-e2-e-app/DECISIONS.md) - Architecture decisions, resolved ambiguities, and questions for the PM
- [TRADEOFFS.md](file:///Users/subratgangwar/Documents/Subrat/VsCode/Breatheesg/next-js-e2-e-app/TRADEOFFS.md) - Deliberate scope compromises and rationales
- [SOURCES.md](file:///Users/subratgangwar/Documents/Subrat/VsCode/Breatheesg/next-js-e2-e-app/SOURCES.md) - Research on real-world formats, sample data, and failure modes
- [ARCHITECTURE.md](file:///Users/subratgangwar/Documents/Subrat/VsCode/Breatheesg/next-js-e2-e-app/ARCHITECTURE.md) - System architecture design and API endpoints
