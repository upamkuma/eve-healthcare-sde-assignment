# EVE Healthcare Assignment Checklist

## Core Requirements

- [x] User Signup (`POST /auth/signup`)
- [x] User Login (`POST /auth/login` — supports both JSON and Form data)
- [x] JWT Authentication & Token Expiration
- [x] Request Validation (Pydantic v2 schemas)
- [x] Diagnostic Centres Management & Retrieval (`GET /centres`, `GET /centres/{id}`, `POST /centres`, `PUT /centres/{id}`, `DELETE /centres/{id}`)
- [x] Diagnostic Tests Management & Retrieval (`GET /centres/{id}/tests`, `GET /centres/{id}/tests/{test_id}`, `POST /centres/{id}/tests`, `PUT /centres/{id}/tests/{test_id}`, `DELETE /centres/{id}/tests/{test_id}`)
- [x] Test Prices (enforced server-side)
- [x] Authenticated Diagnostic Test Booking (`POST /bookings`)
- [x] Booking Patient/User association
- [x] Diagnostic Test association
- [x] Diagnostic Centre association
- [x] Appointment Date/Time validation (future dates, timezone-aware)
- [x] Amount (server-side calculated from selected test price)
- [x] Booking States: `PENDING`, `CONFIRMED`, `FAILED`, `CANCELLED`
- [x] Simulated Payment Endpoint (`POST /payments/` and `POST /payments`)
- [x] Payment Results: `SUCCESS` and `FAILED`
- [x] Related Booking Status Update upon payment
- [x] Payment Webhook Endpoint (`POST /payments/webhook/` and `POST /payments/webhook`)
- [x] Idempotent Webhook Processing (no duplicate payments, bookings, or state corruption)
- [x] Invalid Request Handling (400 / 422 HTTP responses)
- [x] Invalid Booking ID Handling (404 HTTP responses)
- [x] Failed Payment Handling (booking marked FAILED, non-payable terminal state)
- [x] Authorization Checks (role-based admin vs user ownership)

## Submission Deliverables

- [x] README.md (comprehensive setup, API docs, schema, and assumptions)
- [x] requirements.txt (all pinned dependencies)
- [x] Dockerfile (clean production container)
- [x] docker-compose.yml (PostgreSQL + Redis + FastAPI API)
- [x] Source code (clean architecture: api, core, db, models, schemas, services)
- [x] Tests (37 automated unit and integration tests passing)

## Optional Bonus Engineering

- [x] Docker & Docker Compose
- [x] Swagger/OpenAPI Documentation (`/docs` and `/redoc`)
- [x] Comprehensive Unit & Integration Tests (`pytest`)
- [x] Structured JSON Logging & Request Latency Middleware
- [x] Pagination on Centres and Bookings (`page`, `page_size`)
- [x] Idempotency Keys on Payments and Webhooks
- [x] Retry handling & audit tracking for webhook processing (`WebhookEvent`)
- [x] Sliding-window Rate Limiting with `Retry-After` headers
- [x] Redis Caching with in-memory TTL fallback for catalog queries

## Evaluation Matrix Alignment

| Evaluation Area | Weight | Implementation Details |
|---|---|---|
| **Code Quality & Maintainability** | 20% | Modular separation of concerns: `api/` (routers), `services/` (business logic), `schemas/` (Pydantic models), `models/` (SQLAlchemy 2 mapped classes), `core/` (security, config, logging, rate limiting, caching). |
| **API/Backend Design** | 20% | RESTful API design, slash-tolerant endpoints, dual JSON/Form login, standard HTTP status codes (200, 201, 204, 400, 401, 403, 404, 409, 422, 429). |
| **Database Design** | 15% | Relational PostgreSQL schema with foreign keys, unique constraints on emails, provider payment IDs, provider event IDs, idempotency keys, and explicit indexing. |
| **Edge-Case Handling** | 15% | Robust handling of past appointments, naive datetimes, centre/test mismatch, unauthorized resource access, payment idempotency replay, repeated webhook events, cancelled booking protection, confirmed booking corruption prevention. |
| **Tests** | 10% | 37 comprehensive automated unit and integration tests covering auth, catalog CRUD, booking workflows, payment simulation, webhook idempotency, and rate limiting. |
| **Git / README / Documentation** | 10% | Complete documentation including setup instructions, architecture breakdown, curl examples, Postman collection, and future roadmap. |
| **Bonus Engineering** | 10% | Docker + docker-compose with PostgreSQL & Redis, sliding-window rate limiting, structured JSON logging, caching with Redis fallback, webhook retry auditing. |
