# Architectural Decisions

## 1. Monorepo Structure (Single Repo, `/frontend` and `/backend`)

**Decision**: Keep frontend and backend in a single repository with two separate folders.

**Rationale**:
- Easier to manage related changes (bump API version, update both simultaneously)
- Simpler to deploy both as a unit to the same infrastructure
- Single PR/commit for coupled features
- Smaller teams can coordinate more easily

**Alternative Considered**: Separate repositories
- **Pros**: Cleaner separation, independent deployments/CI
- **Cons**: More complex to coordinate, harder to track changes across repos

---

## 2. Django REST Framework (Not Next.js API Routes)

**Decision**: Use Django REST Framework for backend instead of Next.js API routes.

**Rationale**:
- You specifically requested Django backend
- Django ORM makes multi-tenant database queries safer and more readable
- DRF provides out-of-box pagination, filtering, serialization
- Mature ecosystem for complex business logic (processors, validation)
- Decouples frontend from backend (can scale/deploy independently)

**Alternative Considered**: Next.js API routes + Prisma/Drizzle
- **Pros**: Single language (TypeScript), simpler deployment
- **Cons**: Django is more robust for this domain

---

## 3. Neon PostgreSQL (Not SQLite or Other)

**Decision**: Use Neon PostgreSQL as the primary database.

**Rationale**:
- You provided Neon connection string
- PostgreSQL supports JSON columns (validation_issues)
- Supports JSONB for audit log changes dict
- Indexes on compound keys (org_id, date, status)
- Serverless/scalable (Neon)
- Multi-tenant ready (RLS policies)

**Alternative Considered**: SQLite
- **Pros**: Zero setup, great for prototyping
- **Cons**: Not suitable for production multi-tenant app, poor concurrency

---

## 4. CSV Upload for SAP (Not OData API)

**Decision**: Accept CSV flat file exports instead of calling SAP OData API.

**Rationale**:
- Easier onboarding: clients can export CSV from SAP UI (no API credentials)
- Works offline/batch
- Less dependent on SAP version/API changes
- Simpler testing with sample data
- Aligns with how most enterprise users already export data

**Alternative Considered**: SAP OData/REST API
- **Pros**: Real-time sync, less manual steps
- **Cons**: Requires VPN access, API credentials, complexity

---

## 5. Manual Review Workflow (Not Auto-Reconciliation)

**Decision**: All records start in NEW status and require analyst approval (APPROVED/REJECTED).

**Rationale**:
- Emissions calculations are critical (legal/compliance)
- Manual review catches anomalies: unusual fuel quantities, reading gaps, etc.
- Audit trail required: who approved what, when, why
- Different organizations have different validation rules
- Aligns with real-world ESG workflows (analyst sign-off)

**Alternative Considered**: Auto-approve if validation passes
- **Pros**: Faster ingestion
- **Cons**: Risk of invalid data in reports, poor audit trail

---

## 6. Token Authentication (Not JWT or OAuth)

**Decision**: Use Django REST Framework's token authentication (simple tokens).

**Rationale**:
- Stateless (no session database needed)
- Simple to implement and test
- Works with SPA frontend (localStorage)
- Sufficient security for internal/B2B platform

**Alternative Considered**: JWT
- **Pros**: Self-contained claims, no lookup needed
- **Cons**: More complex for basic auth, token revocation harder

**Alternative Considered**: OAuth2
- **Pros**: Industry standard, SSO support
- **Cons**: Overkill for first version, adds complexity

---

## 7. Multi-Tenancy via Organization FK (Not Schema-based)

**Decision**: Enforce multi-tenancy via organization_id foreign key and middleware.

**Rationale**:
- Simpler database schema (single public schema)
- Easier to manage and migrate
- Safer: can implement RLS at database level later if needed
- Users, data sources, emissions all linked to org_id

**Alternative Considered**: Schema-per-tenant (PostgreSQL schemas)
- **Pros**: Better isolation, schema versioning per tenant
- **Cons**: Complex migrations, harder to manage, overkill for this app size

---

## 8. Scope Categorization (Scope 1, 2, 3)

**Decision**: Hard-code scope based on data source and emission type.

**Rationale**:
- Scope 1: SAP fuel (direct combustion)
- Scope 2: Utility electricity (purchased energy)
- Scope 3: Travel (indirect, business travel)
- Aligns with GHG Protocol (industry standard)
- Users expect this classification

**Alternative Considered**: User-configurable scopes
- **Pros**: Flexible
- **Cons**: Could lead to errors, unnecessary complexity

---

## 9. Emission Factor Lookup (Hardcoded + Configurable)

**Decision**: Hardcode default factors in `utils.EMISSION_FACTORS`, allow per-record override via tariff/cabin_class.

**Rationale**:
- Default factors are global (diesel = 2.68 kg CO2e/L)
- Utility can specify tariff code to adjust grid mix (coal vs renewable)
- Flight can specify cabin class for multiplier (business = 2.5x)
- Easy to customize in code if organization has specific needs

**Alternative Considered**: Admin UI for factor configuration
- **Pros**: Non-technical users can adjust
- **Cons**: Risk of invalid changes, scope creep, UI complexity

**Future**: Could add admin UI for factor management in v2

---

## 10. Validation Issues (Array of Strings, Not Rules Engine)

**Decision**: Store validation_issues as a JSON array of human-readable strings.

**Rationale**:
- Simple to implement and debug
- Messages are user-friendly ("Missing cabin class for flight")
- Easy to extend (add new checks to flag_validation_issues function)
- Doesn't block ingestion (warnings, not errors)

**Alternative Considered**: Rules engine (e.g., Drools)
- **Pros**: Complex conditional logic
- **Cons**: Overkill, harder to debug, less readable

---

## 11. Pagination via DRF Defaults (50 per page)

**Decision**: Use DRF's PageNumberPagination with 50 records per page.

**Rationale**:
- Balances performance and UX
- Simple cursor-based pagination built-in
- Frontend can request ?page=2 easily

**Alternative Considered**: No pagination
- **Pros**: Simpler API
- **Cons**: Slow for large datasets (1000+ records)

---

## 12. SWR for Frontend Data Fetching (Not React Query)

**Decision**: Use SWR for client-side caching and data fetching.

**Rationale**:
- Lightweight (~6KB)
- Built by Vercel (native Next.js integration)
- Stale-while-revalidate strategy matches ESG use case (slightly stale data OK)
- Simple API (one hook)

**Alternative Considered**: React Query (TanStack Query)
- **Pros**: More features, better UI for mutations
- **Cons**: Heavier, more complex

---

## 13. No ORM for Python Backend (Plain SQL via models)

**Decision**: Use Django ORM for database access (not SQLAlchemy separately).

**Rationale**:
- Django ORM is built-in, handles migrations
- Querysets are composable and safe from SQL injection
- Works well with DRF serializers
- Models define schema, ORM handles queries

**Alternative Considered**: SQLAlchemy
- **Pros**: Lighter weight, decoupled from Django
- **Cons**: Redundant (Django ORM already good), extra dependency

---

## 14. Audit Trail (AuditLog table, Not Event Sourcing)

**Decision**: Create immutable AuditLog records for all changes (CREATED, APPROVED, REJECTED, NOTES_ADDED).

**Rationale**:
- Simple, understandable model
- Tracks who did what when
- RawEmission record is current state (queryable)
- AuditLog is historical (append-only)
- Meets compliance requirements

**Alternative Considered**: Event Sourcing
- **Pros**: Complete history reconstruction
- **Cons**: Complex, overkill for this app

---

## 15. No Real-time Sync (Batch Processing Model)

**Decision**: Use batch upload model (CSV upload, then review cycle).

**Rationale**:
- Aligns with typical ESG workflows (monthly/quarterly reporting)
- Simpler architecture (no WebSockets, message queues)
- Users upload data in batches → review → approve
- Can add real-time later if needed (WebSockets, background tasks)

**Alternative Considered**: Real-time streaming
- **Pros**: Live data, instant updates
- **Cons**: More complex, not needed for ESG reporting cycle

---

## 16. Sample Data with Realistic Edge Cases

**Decision**: Provide sample CSVs and JSONs with realistic data including edge cases.

**Rationale**:
- Missing cabin class for flights (requires user input)
- Reading gaps in utility data (flags issues)
- Large fuel quantities (unusual, triggers warning)
- Mixed units (L, gal, kg) → tests normalization
- Helps understand system without production data

---

## 17. Next.js App Router (Not Pages Router)

**Decision**: Use Next.js 16 App Router (not Pages Router).

**Rationale**:
- Modern, recommended approach
- Supports server components
- Better file structure
- Middleware support for auth redirects
- Future-proof

---

## 18. Tailwind CSS v4 + shadcn/ui

**Decision**: Use Tailwind CSS 4 and shadcn/ui component library.

**Rationale**:
- Pre-installed in the project
- shadcn provides accessible, unstyled components
- Tailwind is industry standard for React
- Rapid UI development
- Works well with TypeScript

---

## Future Considerations

These decisions were made for v1, but can be revisited:

1. **Real-time updates**: Add WebSockets for live dashboard
2. **Background jobs**: Use Celery for long-running processors
3. **Caching layer**: Redis for analytics aggregation
4. **Data export**: Add Excel/PDF export for reports
5. **Admin UI**: Create admin panel for factor/organization management
6. **API versioning**: Implement versioning as API grows
7. **GraphQL**: Consider if frontend complexity grows
8. **Mobile app**: Current API is REST-friendly for mobile
9. **Webhook integrations**: SAP, Navan could push data instead of pull
10. **Machine learning**: Anomaly detection for outlier emissions

---

## Questions for the PM

If we could align with the Product Manager, these are the critical questions we would ask to refine the product spec:
1.  **Spend-Based Estimation Fallback**: For SAP procurement data, we occasionally see fuel quantities omitted while cost is provided. Should we implement a spend-based emission calculation model (e.g. using EEIO factors) as a fallback when activity values (Liters/kg) are missing?
2.  **Revision/Unlock Policy**: If an auditor rejects a record that has already been signed off and approved, what should the workflow be? Can an admin unlock an approved record (creating a new audit log), or should we enforce separate debit/credit adjustment records to preserve the ledger's integrity?
3.  **Geographic Specificity for Hotels**: Currently, we use a flat baseline of 10 kg CO₂e per room-night for hotels. Since hotel emissions depend heavily on the local grid (e.g., heating fuel and grid mix in the host country), can we request hotel locations (countries) to apply regional DEFRA factors?
4.  **Configurable Warning Thresholds**: The warnings for high electricity consumption (>100,000 kWh) or high fuel quantities (>10,000 L) are currently hardcoded. Can we make these alert thresholds configurable per client facility in a future release?

---

## Data Source Boundaries (Subset Handled vs. Ignored)

To deliver a high-quality prototype within the timeframe, we drew strict boundaries around the inputs:

### 1. SAP Fuel & Procurement
*   **Subset Handled**: CSV exports containing fuel-related purchase orders (Diesel, Petrol, LPG, Natural Gas). Standardized English headers and standard German variants (e.g. `Menge`, `Werk`) are mapped, and plant codes (`PLANT-A`, `PLANT-B`, `PLANT-C`) are translated to physical facility contexts.
*   **What We Ignored**: Miscellaneous procurement categories that do not impact energy emissions (parsed as category `OTHER` and assigned zero emissions), VAT and tax calculations, currency conversions (assumed matching target organization currency), and vendor transportation freight logs.

### 2. Utility Electricity
*   **Subset Handled**: Cumulative interval readings of active electricity meters (kWh) grouped into billing cycles, checking for reading gaps.
*   **What We Ignored**: Complex multi-tariff billing (peak vs. off-peak hours), reactive power (kVARh) records, other utility pipes (water, steam, sewer), and sub-meter splits for sub-leased spaces.

### 3. Corporate Travel
*   **Subset Handled**: SFTP JSON logs containing completed flights (utilizing cabin class multipliers and origin/destination airport IATA codes to calculate distance), hotel stays (total room-nights), and ground transport segments (taxi, bus, train) in kilometers.
*   **What We Ignored**: Multi-leg flight layovers (which are treated as direct point-to-point flights in geocoding), baggage fees, reward point purchases, emissions from meals/dining, rental car refuel receipts, and flight cancellations/refund logs.

