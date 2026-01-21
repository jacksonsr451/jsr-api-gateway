# API Gateway (FastAPI)

API gateway service built with FastAPI and Poetry. It provides CORS, versioned
routes, JWT validation via an external auth service, rate limiting, and a
YAML-backed proxy router with regex matching and rewrites.

## Features

- Versioned API prefix (`/api/v1`).
- CORS configurable via environment variables.
- JWT validation + authorization delegated to `auth_service`.
- Rate limiting with `X-RateLimit-*` headers.
- Dynamic proxy routes stored in `routes.yaml`.
- Admin CRUD endpoints to manage routes.

## Requirements

- Python 3.11+
- Poetry

## Quick start

```bash
poetry install
cp env.example .env
poetry run fastapi run
```

The `fastapi` command is wrapped to load `.env` and use `APP_HOST`/`APP_PORT`
automatically. You can also run Uvicorn directly:

```bash
set -a; source .env; set +a
poetry run uvicorn app.main:app --reload --host $APP_HOST --port $APP_PORT
```

## Health

```
GET /api/v1/health
```

## Route management (admin)

All route management endpoints require the permission configured in
`ROUTES_ADMIN_PERMISSION` (default: `gateway:routes:manage`).

- `GET /api/v1/routes`
- `GET /api/v1/routes/{route_id}`
- `POST /api/v1/routes`
- `PUT /api/v1/routes/{route_id}`
- `DELETE /api/v1/routes/{route_id}`

## Proxy routing (YAML)

Routes are stored in the YAML file configured by `ROUTES_CONFIG_PATH`
(default: `routes.yaml`).

Example:

```yaml
routes:
  - id: users
    name: users-service
    methods: ["GET"]
    regex: "^/users/(\\d+)$"
    upstream_base_url: "http://users:8000"
    rewrite:
      regex_uri: ["^/users/(\\d+)$", "/members/\\1"]
    auth:
      required: true
      permission: "users:read"
      roles: ["admin"]
    priority: 10
    enabled: true
```

Notes:
- Matching uses regex against the request path.
- Routes are sorted by `priority` (higher wins).
- `rewrite.regex_uri` uses Python `re.sub` replacement syntax.
- If any of `auth.required`, `auth.permission`, or `auth.roles` is set,
  the request must have a valid `Authorization: Bearer <token>` header.

## Auth service integration

The gateway delegates token validation and permission checks to `auth_service`.
Configure the endpoints with:

- `AUTH_SERVICE_BASE_URL`
- `AUTH_SERVICE_VALIDATE_PATH`
- `AUTH_SERVICE_AUTHORIZE_PATH`
- `AUTH_SERVICE_TIMEOUT_SECONDS`

The `roles` check expects a `roles` claim (string or list) in the validation
response.

## Rate limiting

Rate limiting is in-memory per process. Configure with:

- `RATE_LIMIT_ENABLED`
- `RATE_LIMIT_REQUESTS`
- `RATE_LIMIT_WINDOW_SECONDS`
- `RATE_LIMIT_EXEMPT_PATHS`
- `RATE_LIMIT_KEY_HEADER` (defaults to `X-Forwarded-For`)

## Configuration

Key settings are read from `.env` (see `env.example`):

- App: `APP_NAME`, `APP_ENV`, `APP_HOST`, `APP_PORT`, `LOG_LEVEL`
- API: `API_PREFIX`
- CORS: `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_METHODS`, `CORS_ALLOW_HEADERS`,
  `CORS_ALLOW_CREDENTIALS`
- Auth: `AUTH_SERVICE_*`
- Rate limit: `RATE_LIMIT_*`
- Proxy: `ROUTES_CONFIG_PATH`, `PROXY_TIMEOUT_SECONDS`,
  `ROUTES_ADMIN_PERMISSION`

## Tests

```bash
poetry run pytest
```

With coverage:

```bash
poetry run pytest --cov=app --cov-report=term-missing --cov-fail-under=85
```
