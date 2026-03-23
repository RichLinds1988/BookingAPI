# Booking API

A production-ready RESTful booking API built with Flask, PostgreSQL, and Redis. Features JWT authentication with refresh tokens, Redis caching, rate limiting, database migrations, structured JSON logging, request tracing, role-based access control, and OpenAPI documentation.

Pairs with the [BookingUI](https://github.com/RichLinds1988/BookingUI) frontend built in React + TypeScript.

## Stack

- **Flask** — API framework
- **PostgreSQL 16** — persistent storage
- **Redis 7** — response caching + rate limiter storage
- **Flask-JWT-Extended** — JWT authentication with refresh tokens
- **Flask-Limiter** — per-route rate limiting
- **Flask-Migrate** — database schema migrations
- **Flask-CORS** — cross-origin request handling
- **Flasgger** — OpenAPI/Swagger documentation
- **Gunicorn** — production WSGI server
- **SQLAlchemy** — ORM
- **Docker Compose** — local orchestration

## Getting Started

### Prerequisites

- Docker + Docker Compose

### Run (development)

```bash
git clone https://github.com/RichLinds1988/BookingAPI.git
cd BookingAPI
docker compose up --build
```

The API will be available at `http://localhost:5000`.

### Run (production)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
```

Production mode uses Gunicorn with 4 workers, removes exposed DB/Redis ports, and sets resource limits.

> PostgreSQL and Redis are started first via healthchecks — the API container waits until both are ready before accepting traffic. Migrations run automatically on startup.

### Environment Variables

Copy `.env.example` to `.env` and adjust for production:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-change-me` | Flask secret key |
| `JWT_SECRET_KEY` | `dev-jwt-secret-change-me` | JWT signing key |
| `JWT_ACCESS_TOKEN_EXPIRES` | `3600` | Access token TTL in seconds |
| `JWT_REFRESH_TOKEN_EXPIRES_DAYS` | `7` | Refresh token TTL in days |
| `DB_HOST` | `db` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_USER` | `booking_user` | PostgreSQL user |
| `DB_PASSWORD` | `booking_password` | PostgreSQL password |
| `DB_NAME` | `booking_db` | PostgreSQL database name |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |

---

## API Documentation

Interactive Swagger UI is available at **http://localhost:5000/apidocs** when the app is running.

Click **Authorize** and enter `Bearer <your_token>` to test protected endpoints directly from the browser.

---

## API Reference

All protected routes require the `Authorization: Bearer <token>` header.

### Health

#### `GET /health`

Returns the status of all dependencies. Used by Kubernetes liveness/readiness probes.

**Response `200`**
```json
{
  "status": "ok",
  "dependencies": {
    "database": "ok",
    "redis": "ok"
  }
}
```

Returns `503` if any dependency is down.

---

### Auth

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register a new user |
| `POST` | `/api/auth/login` | Login and get tokens |
| `POST` | `/api/auth/refresh` | Get a new access token using a refresh token |
| `PATCH` | `/api/auth/users/:id/promote` | Promote a user to admin (admin only) |

Both `register` and `login` return an access token (1 hour) and a refresh token (7 days):

```json
{
  "user": { "id": 1, "email": "rich@example.com", "name": "Rich", "role": "user" },
  "access_token": "<jwt>",
  "refresh_token": "<jwt>"
}
```

When the access token expires, call `/api/auth/refresh` with the refresh token in the `Authorization` header to get a new access token without re-logging in.

---

### Resources

Bookable resources (rooms, desks, equipment, etc.). **Create and update require admin role.**

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/resources` | List active resources (paginated) |
| `GET` | `/api/resources/:id` | Get a single resource |
| `POST` | `/api/resources` | Create a resource 🔒 admin |
| `PATCH` | `/api/resources/:id` | Update a resource 🔒 admin |

#### Pagination

List endpoints support `?page=1&per_page=20` query params and return:

```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 45,
    "pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

---

### Bookings

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/bookings` | List your bookings (paginated) |
| `GET` | `/api/bookings/:id` | Get a booking |
| `POST` | `/api/bookings` | Create a booking |
| `DELETE` | `/api/bookings/:id` | Cancel a booking |
| `GET` | `/api/bookings/availability/:resource_id` | Check availability |

#### Create booking body

```json
{
  "resource_id": 1,
  "start_time": "2026-06-01T09:00:00",
  "end_time": "2026-06-01T10:00:00",
  "guests": 5,
  "notes": "Team standup"
}
```

Validated against the resource's `capacity` — returns `422` if guests exceed capacity.

---

## Roles

| Role | Can book | Can manage resources |
|---|---|---|
| `user` (default) | ✅ | ❌ |
| `admin` | ✅ | ✅ |

To promote a user to admin, use `PATCH /api/auth/users/:id/promote` (requires an existing admin token). The first admin must be set directly in the database:

```bash
docker compose exec db psql -U booking_user -d booking_db -c \
  "UPDATE users SET role='admin' WHERE email='your@email.com';"
```

---

## Rate Limits

| Endpoint | Limit |
|---|---|
| `POST /api/auth/register` | 10 / hour |
| `POST /api/auth/login` | 20 / hour |
| `POST /api/auth/refresh` | 60 / hour |
| `POST /api/bookings` | 30 / hour |
| `GET` routes | 60 / minute |

Limits are stored in Redis and shared across all API instances.

---

## Project Structure

```
BookingAPI/
├── src/
│   ├── config.py
│   └── app/
│       ├── __init__.py               # App factory, extensions
│       ├── models.py                 # SQLAlchemy models (User, Resource, Booking)
│       ├── middleware/
│       │   ├── cache.py              # Redis cache decorator + invalidation helper
│       │   ├── request_id.py         # Unique request ID middleware
│       │   └── request_logger.py     # Structured JSON request logging
│       ├── routes/
│       │   ├── auth.py               # /api/auth
│       │   ├── bookings.py           # /api/bookings
│       │   ├── resources.py          # /api/resources
│       │   └── health.py             # /health
│       └── utils/
│           ├── decorators.py         # admin_required decorator
│           ├── logging.py            # JSON log formatter
│           └── pagination.py         # Reusable pagination helper
├── tests/                            # pytest unit + integration tests
├── migrations/                       # Flask-Migrate migration files
├── boot.py                           # Flask CLI entry point
├── run.py                            # App entry point
├── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml           # Production overrides
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

## Running Tests

```bash
docker compose --profile test run test
```

Tests use SQLite in-memory — no PostgreSQL or Redis required. 54 tests covering auth, bookings, resources, models, and health check.

## Running CI Checks Locally

**Flake8:**
```bash
docker compose run --rm api bash -c "pip install -r requirements-dev.txt && flake8 src/app/ --max-line-length=120 --ignore=E501,W503"
```

**Mypy:**
```bash
docker compose run --rm api bash -c "pip install -r requirements-dev.txt && mypy src/app/"
```

**Tests:**
```bash
docker compose --profile test run test
```

## CI

GitHub Actions runs on every push to `main`:

- **flake8** — style and error checking
- **mypy** — static type checking
- **pytest** — full test suite against PostgreSQL and Redis

## Caching Strategy

GET responses are cached in Redis with a short TTL (30–60s). Write operations (`POST`, `PATCH`, `DELETE`) invalidate relevant cache key patterns immediately to keep reads consistent.

## License

MIT