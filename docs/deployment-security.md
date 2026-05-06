# Production Environment Checklist

## Backend

Copy `backend/.env.example` to `backend/.env` and replace every placeholder value.

Recommended production values:

```env
APP_ENV=production
APP_SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=mysql+pymysql://app_user:strong_password@db-host:3306/dataplatform
CORS_ALLOW_ORIGINS=https://your-frontend-domain.com
ALLOWED_HOSTS=your-api-domain.com
SQLALCHEMY_ECHO=false
```

Notes:

- `APP_SECRET_KEY` must be set in production or the backend will refuse to start.
- `CORS_ALLOW_ORIGINS` must list your real frontend domains.
- `ALLOWED_HOSTS` must list your real backend domain names.
- Do not keep development passwords or localhost domains in production.

## Frontend

Copy `frontend/.env.example` to `frontend/.env` before local development.

For production builds, set:

```env
VITE_API_BASE_URL=https://your-api-domain.com
```

Do not put secrets into any `VITE_` environment variable because those values are exposed to users in the browser.
