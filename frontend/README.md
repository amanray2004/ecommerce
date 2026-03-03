# Frontend (React + Vite)

## Setup

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

## Environment

- `VITE_API_BASE_URL` - FastAPI base URL
- `VITE_KEYCLOAK_URL` - Keycloak base URL (without `/realms/...`)
- `VITE_KEYCLOAK_REALM` - Keycloak realm
- `VITE_KEYCLOAK_CLIENT_ID` - public client used for Swagger/frontend login
- `VITE_DEFAULT_TENANT` - initial tenant shown in storefront

## Notes

- Login button redirects to Keycloak and returns to frontend.
- Frontend calls tenant routes using bearer token from `keycloak-js`.
- When Firebase is not configured, product images still work via backend `/uploads/...` fallback.
