# Horilla CRM v1.0.0 — Release Notes

**Release**: v1.0.0 (initial release)  
**License**: LGPL-2.1  
**Documentation**: `https://docs.horilla.com/crm/functional/v1.0/`  
**Live demo**: `https://crm.demo.horilla.com/`

## Highlights

- **Core CRM suite**: Accounts, Contacts, Leads, Opportunities, Campaigns, and Forecasting shipped together as a cohesive CRM.
- **Lead capture + automation**: Built-in **Web-to-Lead** embeddable forms and **Mail-to-Lead** ingestion (IMAP + Outlook/Graph) to turn inbound interest into tracked Leads.
- **Sales execution tooling**: Opportunity **Team Selling**, **Opportunity Splits**, and configurable **Big Deal Alerts**.
- **Enterprise-ready platform features**: Role/permission controls, multi-language UI, reporting/dashboard foundations, and real-time notification infrastructure (Channels/WebSockets supported).

## What’s included (v1.0)

### People & relationship management

- **Accounts**: Company/organization records.
- **Contacts**: Individual contact records linked to accounts and sales activity.

### Sales pipeline

- **Leads**: Capture, qualification workflow, lead status/stages, and conversion-oriented flow.
- **Opportunities**: Deal tracking with stages plus collaboration controls.

### Lead capture & intake

- **Web-to-Lead form builder**
  - Select Lead fields and generate embeddable HTML
  - Language selection for public forms
  - Optional reCAPTCHA support
  - Configurable post-submit behavior (return URL or success message)
- **Mail-to-Lead**
  - Configure mailboxes to create Leads from inbound email
  - **IMAP** support for standard mailboxes
  - **Outlook (Microsoft Graph)** support with token refresh handling
  - Deduping & thread awareness via message IDs to avoid creating Leads from replies
  - Keyword filtering and sender acceptance controls (per configuration)

### Scoring & prioritization

- **Scoring Rules / Criteria**: Define rule sets per module with conditional operators and points to drive lead prioritization.

### Opportunity collaboration

- **Opportunity Teams**: Define teams, default members, roles, and access levels; apply teams to opportunities.
- **Opportunity Splits**
  - Split opportunity values across users (by amount or expected revenue)
  - Optional enforcement that split totals equal **100%**
  - Optional auto-add of split users into the opportunity team (when configured)
- **Big Deal Alerts**
  - Threshold-based alerts (amount and/or probability)
  - Configurable recipients (including “notify opportunity owner”)
  - Activation toggles

### Forecasting

- Forecast models + utilities for pipeline/best case/commit/closed/actual (amount or quantity based on forecast type).
- Admin command: **`python manage.py recalculate_forecasts`**
  - Supports filtering by `--user-id`, `--fiscal-year-id`, `--forecast-type-id`
  - Includes `--dry-run` to preview changes

### API foundations

- Module REST endpoints (Leads/Accounts/Contacts/Opportunities/Campaigns/Forecast) with serializers and routing present.
- OpenAPI tooling included (dependency: `drf-yasg`).

## Deployment & operations

- **Docker-supported** workflow (per project documentation).
- **Debian package integration** includes:
  - systemd service configuration
  - automatic migrations
  - static file collection
  - log rotation support
  - security hardening with a dedicated service user
- **Database support**: PostgreSQL recommended; MySQL/MariaDB and SQLite supported for development/testing.

## Compatibility / requirements

- **Python**: 3.12+  
- **Django**: pinned in `requirements.txt` (currently `Django==6.0`)  
- **Optional**: Redis for scaled WebSocket/Channels deployments

## Upgrade notes

**v1.0.0 is the first public release**, so there are no upgrade steps from prior Horilla CRM versions beyond standard initial setup:

- Run migrations (`python manage.py migrate`)
- Collect static files (if applicable to your deployment)
- Create an admin user (`python manage.py createsuperuser`)
- Configure email ingestion and Redis (optional) as needed

