# Quick Start Guide

## Prerequisites
- Python 3.9+ (for Django backend)
- Node.js 18+ (for Next.js frontend)
- Neon PostgreSQL account (for database)
- Git

## 1. Clone & Install

```bash
# Clone the repo (you already have it)
cd /vercel/share/v0-project

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy env file
cp .env.example .env
# Edit .env with your Neon DATABASE_URL

# Frontend setup
cd ../frontend
npm install  # or pnpm install or yarn install

# Copy env file
cp .env.example .env.local
# Verify NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

## 2. Database Setup

```bash
cd backend

# Run migrations
python manage.py migrate

# Create test user (optional)
python manage.py createsuperuser
# Email: demo@example.com
# Password: demo1234
# Use the same in Next.js login
```

## 3. Start Services

**Terminal 1 - Django Backend:**
```bash
cd backend
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
# Backend at http://localhost:8000
# Admin panel at http://localhost:8000/admin
```

**Terminal 2 - Next.js Frontend:**
```bash
cd frontend
npm run dev  # or pnpm dev
# Frontend at http://localhost:3000
```

## 4. Test the System

### Create Organization & User (via Django Admin)
1. Go to http://localhost:8000/admin
2. Log in with superuser credentials
3. Add Organization: Name="Acme Corp", email_domain="acme.com"
4. Add UserProfile: Link user to org, set role=ANALYST
5. Note the organization ID

Reminder: Always run `source venv/bin/activate` first in every new terminal session before running any `python3 manage.py` commands.

### Get Auth Token
```bash
curl -X POST http://localhost:8000/api-token-auth/ \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "demo1234"}'
# Returns: {"token": "abc123..."}
```

### Test Ingestion (SAP)
```bash
# Create a simple CSV
cat > /tmp/test.csv << EOF
PO#,Material Code,Plant Code,Date,Quantity,Unit of Measure,Cost,Vendor
001,FUEL-DIESEL-100,PLANT-A,2024-01-15,500,L,1250,Shell
EOF

# Upload
curl -X POST http://localhost:8000/api/ingestion/sap/ \
  -H "Authorization: Token abc123..." \
  -F "file=@/tmp/test.csv"
```

### Test Frontend
1. Go to http://localhost:3000/login
2. Enter: demo@example.com / demo1234
3. You should see the dashboard
4. Click "Ingest Data" to upload the SAP CSV

## Sample Data

Use the files in `/sample-data/`:
- `sap_example.csv` - 10 fuel purchase orders
- `utility_example.csv` - Meter readings for 2 locations
- `travel_example.json` - Mixed travel expenses (flights, hotels, ground)

Upload any of these from the Ingest Data page.

## Testing Workflow

1. **Upload SAP CSV**
   - Go to /ingest, SAP tab
   - Upload sample-data/sap_example.csv
   - Should show 10 records ingested

2. **Review Dashboard**
   - Go to /dashboard
   - See all NEW records
   - Click a row to open modal
   - View details, validation issues, audit log

3. **Approve Records**
   - Click "Approve" in modal
   - Record moves to APPROVED status
   - Audit log shows timestamp and approver

4. **View Analytics**
   - Go to /analytics
   - Should show:
     - Scope 1: sum of all fuel emissions
     - Category breakdown
     - Status counts

## Troubleshooting

### CORS Error: "Access to XMLHttpRequest blocked"
- Check CORS_ALLOWED_ORIGINS in backend/config/settings.py
- Add frontend URL (http://localhost:3000)
- Restart Django

### Database Connection Error
- Verify DATABASE_URL in backend/.env
- Test connection: `python manage.py dbshell`
- Check if Neon database is running

### 401 Unauthorized (API calls)
- Verify token in Authorization header
- Check token isn't expired (simple tokens don't expire, but check Django settings)
- Verify user has a UserProfile linked to organization

### CSV Upload Returns 400
- Check headers match expected format
- Look at error messages in response
- Verify it's valid CSV format (no extra quotes, proper escaping)

### Data not showing in dashboard
- Verify records were created (check response from upload)
- Confirm organization_id matches user's org
- Check filters aren't filtering out records

## Deployment Checklist

### Backend (Django)

1. **Environment Variables**
   ```
   DATABASE_URL=postgresql://...
   SECRET_KEY=generate with django.core.management.get_random_secret_key()
   DEBUG=False
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   CORS_ALLOWED_ORIGINS=https://yourdomain.com
   ```

2. **Security Settings**
   ```python
   # settings.py
   SECURE_SSL_REDIRECT = True
   SESSION_COOKIE_SECURE = True
   CSRF_COOKIE_SECURE = True
   SECURE_HSTS_SECONDS = 31536000
   ```

3. **Deployment**
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   gunicorn config.wsgi:application
   ```

### Frontend (Next.js)

1. **Environment Variables**
   ```
   NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api
   ```

2. **Build & Deploy**
   ```bash
   npm run build
   npm run start
   # Or push to Vercel (auto-deploys)
   ```

## Next Steps

1. **Customize emission factors**: Edit `backend/emissions/utils.py`
2. **Add more data sources**: Follow `SAPProcessor` pattern
3. **Real-time updates**: Add WebSockets + Django Channels
4. **Background jobs**: Use Celery for async processing
5. **Admin UI**: Create pages for organization/factor management
6. **Export reports**: Add Excel/PDF export endpoints

## Support

- See `ARCHITECTURE.md` for system design
- See `DECISIONS.md` for design rationale
- See `README.md` for full API docs
- Check error messages in browser console (frontend) and Django logs (backend)

---

**Status**: Ready for production (with proper env vars and HTTPS)
**Last Updated**: 2024-05-27
