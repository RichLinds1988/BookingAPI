# Booking API

A RESTful booking API built with Flask, PostgreSQL, and Redis. Supports JWT authentication, Redis caching, rate limiting, database migrations, and a health check endpoint. Runs fully containerized via Docker Compose.

Pairs with the [booking-ui](https://github.com/RichLinds1988/booking-ui) frontend built in React + TypeScript.

## Stack

- **Flask** — API framework
- **PostgreSQL 16** — persistent storage
- **Redis 7** — response caching + rate limiter storage
- **Flask-JWT-Extended** — JWT authentication
- **Flask-Limiter** — per-route rate limiting
- **Flask-Migrate** — database schema migrations
- **SQLAlchemy** — ORM
- **Docker Compose** — local orchestration

## Getting Started

### Prerequisites

- Docker + Docker Compose

### Run

```bash
git clone https://github.com/RichLinds1988/BookingAPI.git
cd BookingAPI
docker compose up --build
```

The API will be available at `http://localhost:5000`.

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
| `DB_HOST` | `db` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_USER` | `booking_user` | PostgreSQL user |
| `DB_PASSWORD` | `booking_password` | PostgreSQL password |
| `DB_NAME` | `booking_db` | PostgreSQL database name |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `JWT_ACCESS_TOKEN_EXPIRES` | `3600` | Token TTL in seconds |

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

#### `POST /api/auth/register`

```json
{
  "name": "Rich",
  "email": "rich@example.com",
  "password": "supersecret"
}
```

**Response `201`**
```json
{
  "user": { "id": 1, "email": "rich@example.com", "name": "Rich" },
  "access_token": "<jwt>"
}
```

---

#### `POST /api/auth/login`

```json
{
  "email": "rich@example.com",
  "password": "supersecret"
}
```

**Response `200`**
```json
{
  "user": { "id": 1, "email": "rich@example.com", "name": "Rich" },
  "access_token": "<jwt>"
}
```

---

### Resources

Bookable resources (rooms, desks, equipment, etc.).

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/resources` | List active resources (paginated) |
| `GET` | `/api/resources/:id` | Get a single resource |
| `POST` | `/api/resources` | Create a resource |
| `PATCH` | `/api/resources/:id` | Update a resource |

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

#### Create resource body

```json
{
  "name": "Boardroom A",
  "description": "10-person boardroom, projector included",
  "capacity": 10
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

#### Check availability

```
GET /api/bookings/availability/1?start_time=2026-06-01T09:00:00&end_time=2026-06-01T10:00:00
```

```json
{
  "resource_id": 1,
  "available": true,
  "start_time": "2026-06-01T09:00:00",
  "end_time": "2026-06-01T10:00:00"
}
```

---

## Rate Limits

| Endpoint | Limit |
|---|---|
| `POST /api/auth/register` | 10 / hour |
| `POST /api/auth/login` | 20 / hour |
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
│       ├── __init__.py          # App factory, extensions
│       ├── models.py            # SQLAlchemy models (User, Resource, Booking)
│       ├── middleware/
│       │   └── cache.py         # Redis cache decorator + invalidation helper
│       ├── routes/
│       │   ├── auth.py          # /api/auth
│       │   ├── bookings.py      # /api/bookings
│       │   ├── resources.py     # /api/resources
│       │   └── health.py        # /health
│       └── utils/
│           └── pagination.py    # Reusable pagination helper
├── tests/                       # pytest unit + integration tests
├── migrations/                  # Flask-Migrate migration files
├── boot.py                      # Flask CLI entry point
├── run.py                       # App entry point
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

## Running Tests

```bash
docker compose --profile test run test
```

Tests use SQLite in-memory — no PostgreSQL or Redis required. 51 tests covering auth, bookings, resources, models, and health check.

## CI

GitHub Actions runs on every push to `main`:

- **flake8** — style and error checking
- **mypy** — static type checking
- **pytest** — full test suite against PostgreSQL and Redis

## Caching Strategy

GET responses are cached in Redis with a short TTL (30–60s). Write operations (`POST`, `PATCH`, `DELETE`) invalidate relevant cache key patterns immediately to keep reads consistent.

## License

MIT
