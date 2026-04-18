# Booking API

A production-ready RESTful booking API built with FastAPI, PostgreSQL, and Redis. Features JWT authentication with refresh tokens, Redis caching, rate limiting, database migrations, structured JSON logging, request tracing, role-based access control, and interactive OpenAPI documentation.

Pairs with the [BookingUI](https://github.com/RichLinds1988/BookingUI) frontend built in React + TypeScript.

![CI](https://github.com/RichLinds1988/BookingAPI/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/fastapi-0.115-green)
![PostgreSQL](https://img.shields.io/badge/postgres-16-blue)

## Stack

- **FastAPI** — async API framework with built-in OpenAPI docs
- **PostgreSQL 16** — persistent storage
- **Redis 7** — response caching + rate limiter storage
- **SQLAlchemy 2.0** — async ORM with `mapped_column` style models
- **Alembic** — database schema migrations
- **PyJWT** — JWT authentication with access + refresh tokens
- **slowapi** — per-route rate limiting
- **uvicorn** — ASGI server (dev + prod)
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

The API will be available at `http://localhost:8000`.

### Run (production)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
```

Production mode uses uvicorn with 4 workers, removes exposed DB/Redis ports, and sets resource limits.

> PostgreSQL and Redis are started first via healthchecks — the API container waits until both are ready before accepting traffic. Migrations run automatically on startup via Alembic.

### Environment Variables

Copy `.env.example` to `.env` and adjust for production:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET_KEY` | `dev-jwt-secret-change-me` | JWT signing key (use a long random string in prod) |
| `JWT_ACCESS_TOKEN_EXPIRES` | `3600` | Access token TTL in seconds |
| `JWT_REFRESH_TOKEN_EXPIRES` | `604800` | Refresh token TTL in seconds (7 days) |
| `DB_HOST` | `db` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_USER` | `booking_user` | PostgreSQL user |
| `DB_PASSWORD` | `booking_password` | PostgreSQL password |
| `DB_NAME` | `booking_db` | PostgreSQL database name |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |

---

## API Documentation

Interactive Swagger UI is available at **http://localhost:8000/docs** when the app is running.

ReDoc is also available at **http://localhost:8000/redoc**.

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
| `PATCH` | `/api/auth/users/:id/role` | Update a user's role (admin only) |

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

Validated against the resource's `capacity` — returns `422` if guests exceed capacity. Back-to-back bookings are allowed (half-open interval `[start, end)`).

---

## Roles

| Role | Can book | Can manage resources |
|---|---|---|
| `user` (default) | ✅ | ❌ |
| `admin` | ✅ | ✅ |

To promote a user to admin, use `PATCH /api/auth/users/:id/role` with `{"role": "admin"}` (requires an existing admin token). The first admin must be set directly in the database:

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

Limits are stored in Redis and shared across all API instances. Exceeding a limit returns `429` with a `retry_after` field.

---

## Project Structure

```
BookingAPI/
├── src/
│   ├── config.py                     # Environment-based config
│   └── app/
│       ├── main.py                   # FastAPI app factory + lifespan
│       ├── cache.py                  # Redis cache decorator + invalidation
│       ├── limiter.py                # slowapi rate limiter instance
│       ├── database.py               # Async SQLAlchemy engine + session
│       ├── models.py                 # SQLAlchemy models (User, Resource, Booking)
│       ├── schemas.py                # Pydantic v2 request schemas
│       ├── middleware/
│       │   └── request_logger.py     # Structured JSON request logging
│       ├── routes/
│       │   ├── auth.py               # /api/auth
│       │   ├── bookings.py           # /api/bookings
│       │   ├── resources.py          # /api/resources
│       │   └── health.py             # /health
│       └── utils/
│           ├── auth.py               # JWT encode/decode + FastAPI dependencies
│           ├── dependencies.py       # require_admin dependency
│           ├── logging.py            # JSON log formatter
│           └── pagination.py        # Reusable async pagination helper
├── tests/                            # pytest async test suite
├── migrations/                       # Alembic migration files
├── run.py                            # Local dev entry point
├── Makefile                          # Common dev commands
├── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml           # Production overrides
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

## Running Tests

Tests use SQLite in-memory with `aiosqlite` and a mocked Redis client — no running PostgreSQL or Redis required.

```bash
make test
```

56 tests covering auth, bookings, resources, models, and health check.

## Local Development

```bash
make install    # install dependencies
make run        # start uvicorn with hot reload on :8000
make migrate    # run alembic migrations
make test       # run pytest
make lint       # ruff check
make format     # ruff format
make pre-push   # lint + format + tests
```

## CI

GitHub Actions runs on every push to `main`:

- **ruff** — style and import checking
- **mypy** — static type checking
- **pytest** — full test suite

## Caching Strategy

GET responses are cached in Redis with a short TTL (30–60s). Write operations (`POST`, `PATCH`, `DELETE`) invalidate relevant cache key patterns immediately to keep reads consistent.

## License

MIT
