# MezFlow — Module 0: Foundation & Project Scaffolding
## Implementation Plan (`M0_implementation_plan.md`)

- **Project:** MezFlow — Real-Time Restaurant Dining and Kitchen Operations Management System
- **Phase:** FYP-I (Preparation & Baseline Foundation)
- **Document Version:** 1.0
- **Target Location:** `Docs/Plan/M0_implementation_plan.md`
- **Traceability:** Supports `NFR-08` (Multi-tenant isolation), `NFR-14` (Modular layered architecture & versioned migrations), `NFR-15` (PWA & Docker packaging), `NFR-16` (Scalability).

---

## 1. Objective & Scope of Module 0

Module 0 sets up the foundational engineering infrastructure before feature code for **M1 (Identity & Access)** and **M2 (Digital Menu)** is written. Completing Module 0 ensures that every developer on the team (Khizar, Talha, Sail) works on a synchronized, containerized, and type-safe development environment with zero configuration drift.

### Key Deliverables of M0:
1. **Monorepo Directory Structure**: Clean separation between `backend`, `frontend`, `docker`, and `docs`.
2. **Containerized Local Environment**: `docker-compose` managing PostgreSQL 16 and Redis (for WebSocket pub/sub).
3. **Backend Service Skeleton**: FastAPI application factory, Pydantic v2 settings, async SQLAlchemy session handling, and Alembic database migration pipeline.
4. **Frontend Application Skeleton**: Next.js (App Router, TypeScript, Tailwind CSS) configured with route groups for the Diner PWA, Kitchen Display System (KDS), and Management Console.
5. **Database Baseline & Seed Engine**: Initial multi-tenant schema with seeding scripts for dummy restaurant data (tables, menu items, roles).
6. **Code Quality & CI Pipeline**: Linting, formatting (Ruff / ESLint), `pytest` test runner, and GitHub Actions workflow.

---

## 2. Target Workspace Architecture

```text
MezFlow/
├── .github/
│   └── workflows/
│       └── ci.yml                   # Automated linting & test runner
├── Docs/
│   ├── Plan/
│   │   ├── M0_implementation_plan.md
│   │   └── M1_implementation_plan.md
│   ├── MezFlow-FYP-Chapter1-v5.pdf
│   └── MezFlow_Chapter2_SRS.pdf
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/                  # Versioned API routers
│   │   │   │   └── api.py           # Master router aggregator
│   │   │   └── deps.py              # Common FastAPI dependencies (DB, Current User)
│   │   ├── core/
│   │   │   ├── config.py            # Environment settings (Pydantic BaseSettings)
│   │   │   ├── security.py          # Password hashing & JWT helpers (prepared for M1)
│   │   │   └── database.py          # Async engine & sessionmaker
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── base.py              # Base class with ID & timestamps
│   │   │   ├── restaurant.py        # Multi-tenant root entity
│   │   │   ├── user.py              # User & role models
│   │   │   ├── table.py             # Table entity
│   │   │   └── menu.py              # Menu category & item models
│   │   ├── schemas/                 # Pydantic validation schemas
│   │   ├── services/                # Business logic layer
│   │   └── main.py                  # FastAPI entry point & CORS configuration
│   ├── alembic/                     # Database migrations
│   │   ├── env.py
│   │   └── versions/
│   ├── tests/
│   │   ├── conftest.py              # Test database fixtures & async HTTP client
│   │   └── test_health.py           # Healthcheck verification test
│   ├── Dockerfile
│   ├── requirements.txt             # Locked Python dependencies
│   ├── pyproject.toml               # Tooling configs (ruff, pytest)
│   └── alembic.ini
├── frontend/
│   ├── public/                      # Static assets, PWA icons, manifest.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── (customer)/          # Customer PWA route group (M2, M3)
│   │   │   │   └── r/[restaurantId]/t/[tableId]/page.tsx
│   │   │   ├── (kds)/               # Kitchen Display route group (M4)
│   │   │   │   └── kds/page.tsx
│   │   │   ├── (admin)/             # Management Console route group (M10)
│   │   │   │   └── admin/page.tsx
│   │   │   ├── api/                 # Next.js API routes (if needed)
│   │   │   ├── layout.tsx           # Global root layout with Inter font
│   │   │   └── page.tsx             # Landing / portal switcher
│   │   ├── components/              # Shared UI components (Modals, Badges, Buttons)
│   │   ├── lib/                     # Utilities (API client, WebSocket client, formatting)
│   │   ├── types/                   # Shared TypeScript interfaces
│   │   └── styles/
│   │       └── globals.css          # Tailwind CSS directives & color tokens
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── next.config.ts
├── docker/
│   └── nginx/
│       └── default.conf             # Local reverse proxy configuration
├── docker-compose.yml               # Production/staging orchestration
├── docker-compose.dev.yml           # Local dev with hot-reloading
├── .env.example                     # Environment template
├── .gitignore
└── README.md
```

---

## 3. Step-by-Step Implementation Sequence

```mermaid
flowchart TD
    subgraph Phase 1: Repo & Environment Setup
        T1["T0.1: Git Repository & .gitignore Configuration"]
        T2["T0.2: Docker Compose & Services (PostgreSQL + Redis)"]
        T3["T0.3: Environment Configuration (.env.example)"]
    end

    subgraph Phase 2: Backend Scaffolding
        T4["T0.4: FastAPI App Factory & Healthcheck Endpoints"]
        T5["T0.5: Async SQLAlchemy 2.0 & DB Connection Pool"]
        T6["T0.6: Alembic Migrations Setup & Initial Baseline"]
    end

    subgraph Phase 3: Frontend Scaffolding
        T7["T0.7: Next.js + TypeScript + Tailwind Setup"]
        T8["T0.8: Route Groups & PWA Manifest Configuration"]
        T9["T0.9: Unified Axios/Fetch API Client & Error Handler"]
    end

    subgraph Phase 4: Database Seeding & Verification
        T10["T0.10: Database Seed Script (Demo Restaurant, Tables, Menu)"]
        T11["T0.11: Pytest Test Suite Setup & Health Check Test"]
        T12["T0.12: Definition of Done Verification"]
    end

    T1 --> T2 --> T3
    T3 --> T4 --> T5 --> T6
    T3 --> T7 --> T8 --> T9
    T6 --> T10
    T4 --> T11
    T9 --> T12
    T10 --> T12
    T11 --> T12
```

---

### Phase 1: Git & Environment Setup

#### Task 0.1: Repository Configuration & `.gitignore`
- Create `.gitignore` covering Python (`__pycache__`, `.venv/`, `*.pyc`), Node.js (`node_modules/`, `.next/`), environment files (`.env`), and IDE configurations.
- Ensure root level documentation (`Docs/`) is tracked properly.

#### Task 0.2: Dockerized Environment (`docker-compose.dev.yml`)
- **PostgreSQL 16**: Port `5432`, volume mapped for data persistence, database name: `mezflow_db`.
- **Redis 7 (Alpine)**: Port `6379`, for caching and WebSocket pub/sub message brokering.
- Provide healthcheck commands inside Docker Compose so services wait for PostgreSQL readiness.

#### Task 0.3: Environment Template (`.env.example`)
Define required environment keys:
```env
# Backend Settings
PROJECT_NAME="MezFlow"
ENVIRONMENT="development"
SECRET_KEY="temporary-dev-secret-change-in-production"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Database
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=mezflow_db
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mezflow_db

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

---

### Phase 2: Backend Scaffolding (FastAPI + Async SQLAlchemy)

#### Task 0.4: FastAPI App Factory & Healthcheck
- Initialize `backend/requirements.txt` with locked versions:
  - `fastapi`, `uvicorn[standard]`, `pydantic[email]`, `pydantic-settings`
  - `sqlalchemy[asyncio]`, `asyncpg`, `alembic`
  - `passlib[bcrypt]`, `python-jose[cryptography]`
  - `pytest`, `pytest-asyncio`, `httpx`
- Create `backend/app/main.py`:
  - Initialize FastAPI with title `"MezFlow API"`.
  - Configure CORS middleware allowing requests from `http://localhost:3000`.
  - Add `/api/health` endpoint returning database connection status and server timestamp.

#### Task 0.5: Database Session Manager (`backend/app/core/database.py`)
- Configure `create_async_engine` with connection pooling (`pool_size=10`, `max_overflow=20`).
- Create `async_sessionmaker` and a reusable dependency `get_db()` yielding an `AsyncSession`.
- Create base declarative model with auto-generating UUIDs and `created_at` / `updated_at` UTC timestamps.

#### Task 0.6: Alembic Migrations Setup
- Initialize Alembic with async template: `alembic init -t async alembic`.
- Modify `alembic/env.py` to import `Base.metadata` and resolve database URL from `app.core.config.settings`.
- Prepare initial migration pipeline.

---

### Phase 3: Frontend Scaffolding (Next.js 14+ / 15)

#### Task 0.7: Next.js Initialization & Styling Tokens
- Initialize Next.js project with TypeScript, Tailwind CSS, and ESLint.
- Set up design tokens in `tailwind.config.ts`:
  - Brand colors: Primary (warm saffron/orange accents), Neutral (slate dark-mode palette), Status colors (Green/Ready, Blue/Preparing, Amber/New, Red/Delayed).
  - Modern typography: Configure `Inter` font.

#### Task 0.8: Application Route Groups
Configure distinct layout wrappers for the three MezFlow personas:
1. `(customer)/r/[restaurantId]/t/[tableId]/`:
   - Mobile viewport locked layout (`viewport-fit=cover`).
   - PWA meta tags configured (`manifest.json`, theme colors).
2. `(kds)/kds/`:
   - High-contrast, full-screen dashboard layout designed for kitchen tablets/monitors.
3. `(admin)/admin/`:
   - Management console layout with sidebar navigation.

#### Task 0.9: Standardized API & WebSocket Client
- Create a lightweight Axios / Fetch client (`frontend/src/lib/api.ts`) with:
  - Automatic base URL injection.
  - JWT token interception from localStorage/cookies.
  - Standardized error parsing.

---

### Phase 4: Database Seeding & Verification

#### Task 0.10: Database Seed Script (`backend/scripts/seed.py`)
Create a CLI script to populate a rich demo dataset for instant local testing:
- 1 Demo Restaurant: *"MezFlow Bistro"*
- 10 Tables: Table 1 through Table 10 with pre-computed tokens.
- 5 Menu Categories: *Starters, BBQ & Grill, Main Course, Fast Food, Beverages*.
- 10 Sample Dishes with modifiers (e.g., Spice Levels: *Mild, Medium, Hot*; Add-ons: *Cheese, Sauces*).
- 5 Test User Accounts (one for each role: Customer, Kitchen, Service, Cashier, Manager).

#### Task 0.11: Pytest Test Suite Setup
- Configure `pytest.ini` with `asyncio_mode = auto`.
- Create `backend/tests/conftest.py` with test database fixtures.
- Implement `backend/tests/test_health.py` asserting `GET /api/health` returns `200 OK`.

---

## 4. Definition of Done (DoD) for Module 0

Before moving to **Module 1 (Identity & Access Control)**, the following verification checks must pass:

- [ ] **Docker Service Check**: `docker compose -f docker-compose.dev.yml up -d` starts PostgreSQL and Redis with healthy status.
- [ ] **Backend Health Check**: Running `uvicorn app.main:app --reload` on port 8000 allows `curl http://localhost:8000/api/health` to return `{"status": "healthy", "database": "connected"}`.
- [ ] **Database Migrations Check**: `alembic upgrade head` executes with zero errors.
- [ ] **Seed Script Execution**: Running `python scripts/seed.py` successfully inserts demo restaurant, tables, and categories.
- [ ] **Frontend Dev Server Check**: Running `npm run dev` in `frontend/` opens at `http://localhost:3000` with clean console and working Tailwind CSS styles.
- [ ] **Automated Tests Check**: Running `pytest` in `backend/` passes 100% of basic connectivity tests.

---

## 5. Transition to Module 1

Once Module 0 is verified, development moves directly to **Module 1: Identity & Access Control**, which will implement:
1. `User` and `Role` models and tables.
2. Password hashing via `bcrypt` and JWT issuance / verification.
3. OTP verification flow (mocked for development, ready for SMS/Email in production).
4. FastAPI RBAC dependencies (`require_role(["Manager", "Kitchen Staff"])`).
