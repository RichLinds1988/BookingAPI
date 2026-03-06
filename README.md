# Booking API

A RESTful booking API built with Flask, MySQL, and Redis. Supports JWT authentication, Redis caching, and rate limiting out of the box. Runs fully containerized via Docker Compose.

## Stack

- **Flask** — API framework
- **MySQL 8** — persistent storage
- **Redis 7** — response caching + rate limiter storage
- **Flask-JWT-Extended** — JWT authentication
- **Flask-Limiter** — per-route rate limiting
- **SQLAlchemy** — ORM
- **Docker Compose** — local orchestration

## Getting Started

### Prerequisites

- Docker + Docker Compose

### Run

```bash
git clone https://github.com/RichLinds1988/BookingAPI.git
cd booking-api
docker compose up --build
```

The API will be available at `http://localhost:5000`.

> MySQL and Redis are started first via healthchecks — the API container waits until both are ready before accepting traffic.

## Running Tests
```bash
docker compose --profile test build --no-cache
docker compose --profile test run test
```

Tests use SQLite in-memory and a mocked Redis — no external services required. 50 tests covering auth, bookings, resources, and models.

### Environment Variables

Copy `.env.example` to `.env` and adjust for production:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-change-me` | Flask secret key |
| `JWT_SECRET_KEY` | `dev-jwt-secret-change-me` | JWT signing key |
| `MYSQL_HOST` | `db` | MySQL host |
| `MYSQL_USER` | `booking_user` | MySQL user |
| `MYSQL_PASSWORD` | `booking_password` | MySQL password |
| `MYSQL_DB` | `booking_db` | MySQL database name |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `JWT_ACCESS_TOKEN_EXPIRES` | `3600` | Token TTL in seconds |

---

## API Reference

All protected routes require the `Authorization: Bearer <token>` header.

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
| `GET` | `/api/resources` | List all active resources |
| `GET` | `/api/resources/:id` | Get a single resource |
| `POST` | `/api/resources` | Create a resource |
| `PATCH` | `/api/resources/:id` | Update a resource |

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
| `GET` | `/api/bookings` | List your bookings |
| `GET` | `/api/bookings/:id` | Get a booking |
| `POST` | `/api/bookings` | Create a booking |
| `DELETE` | `/api/bookings/:id` | Cancel a booking |
| `GET` | `/api/bookings/availability/:resource_id` | Check availability |

#### Create booking body

```json
{
  "resource_id": 1,
  "start_time": "2025-06-01T09:00:00",
  "end_time": "2025-06-01T10:00:00",
  "notes": "Team standup"
}
```

#### Check availability

```
GET /api/bookings/availability/1?start_time=2025-06-01T09:00:00&end_time=2025-06-01T10:00:00
```

```json
{
  "resource_id": 1,
  "available": true,
  "start_time": "2025-06-01T09:00:00",
  "end_time": "2025-06-01T10:00:00"
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
booking-api/
├── app/
│   ├── __init__.py          # App factory, extensions
│   ├── models.py            # SQLAlchemy models (User, Resource, Booking)
│   ├── middleware/
│   │   └── cache.py         # Redis cache decorator + invalidation helper
│   └── routes/
│       ├── auth.py          # /api/auth
│       ├── bookings.py      # /api/bookings
│       └── resources.py     # /api/resources
├── config.py                # Config from environment
├── run.py                   # Entrypoint
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Caching Strategy

GET responses are cached in Redis with a short TTL (30–60s). Write operations (`POST`, `PATCH`, `DELETE`) invalidate relevant cache key patterns immediately to keep reads consistent.

## License

MIT
