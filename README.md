# Multi-Tenant Ecommerce Backend (FastAPI)

Production-oriented backend for multi-tenant ecommerce with Keycloak auth, PostgreSQL, SQLAlchemy ORM, Alembic migrations, Firebase Storage image upload, and pytest tests.

## Architecture

```
app/
  main.py
  core/
  db/
  models/
  schemas/
  services/
  routers/
  tests/
alembic/
```

- `routers/`: HTTP layer only (no business logic)
- `services/`: business logic, transactions, stock handling
- `models/`: SQLAlchemy models and relationships
- `core/security.py`: Keycloak JWT validation and role extraction

## Roles

- `platform-admin`
- `tenant-user`
- `customer`

Tenant endpoints are scoped as `/{tenant_name}/...` and enforce tenant-path vs token-tenant checks.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Set environment variables:

```bash
export DATABASE_URL='postgresql+psycopg2://postgres:postgres@localhost:5432/ecommerce'
export KEYCLOAK_ISSUER='https://<keycloak-host>/realms/<realm>'
export KEYCLOAK_AUDIENCE='account'
export KEYCLOAK_PUBLIC_KEY='<realm-public-key>'
export FIREBASE_BUCKET='<bucket-name>'
export FIREBASE_CREDENTIALS_PATH='/path/to/firebase-service-account.json'
```

## Migrations

```bash
alembic upgrade head
```

## Run

```bash
uvicorn app.main:app --reload
```

## Easy Backend Start (Any Terminal)

```bash
cp .env.example .env
# edit .env once
./scripts/run_backend.sh
```

This script activates local `venv`, loads env vars from root `.env`, and starts Uvicorn.

## Tests

```bash
pytest app/tests -q
```
