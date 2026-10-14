Here is a complete, polished `README.md` file designed for your GitHub repository. It clearly presents the project overview, key features, technology stack, project structure, quickstart setup guide, and project roadmap.

---

# MezFlow — Real-Time Restaurant Dining & Kitchen Operations Management System

> **A synchronized, zero-install web platform connecting customer ordering, single-screen kitchen display operations, and table lifecycle management for small and medium restaurants.**

---

## 📌 Project Overview

MezFlow bridges the gap between customer table ordering, kitchen preparation, billing, and management workflows through a real-time, software-only ecosystem.

In typical small and medium restaurants, order taking relies on paper tickets, verbal communication, and disconnected POS software. MezFlow solves these operational bottlenecks by providing:

1. **Zero-Install Collaborative Ordering:** Customers scan a table QR code to browse and build a shared, live cart with fellow diners on their mobile web browser without downloading an app.


2. **Single-Screen Kitchen Display System (KDS):** Replaces paper ticket printers with a software-based digital queue equipped with category filters and automatic preparation delay flags.


3. **Decoupled Table Lifecycle Engine:** Models digital session closure (payment) independently from physical table readiness (staff-confirmed cleanup) to optimize peak-hour table turnover.


4. **Grounded AI Dish Explanation:** Answers customer menu questions in English or Urdu using strictly restaurant-provided structured data.



---

## 🛠 Tech Stack

Built entirely on modern, open-source frameworks and standard web protocols for maximum accessibility and low hosting costs.

* **Frontend:** Next.js (React), TypeScript, Tailwind CSS (Progressive Web App - PWA)


* **Backend API:** Python 3.11+, FastAPI, SQLAlchemy, SQLModel, Alembic


* **Real-Time Communication:** WebSockets (RFC 6455)


* **Database:** PostgreSQL


* **Authentication & Security:** JWT (JSON Web Tokens), bcrypt hashing, Role-Based Access Control (RBAC)


* **DevOps & Infrastructure:** Docker, Docker Compose, Nginx, GitHub Actions



---

## 🚀 Key Features

* **Multi-Tenant Architecture:** Securely supports multiple restaurants on a single database using strict tenant isolation and Row-Level Security (RLS).
* **Collaborative Table Carts:** Live cart updates visible to all diners sitting at the same table, complete with per-item diner attribution.


* **Single-Screen KDS:** Real-time ticket management with category routing (Grill, Fry, Beverages) and preparation timers.


* **Independent State Machines:**
* **Order State:** `NEW` → `CONFIRMED` → `PREPARING` → `READY` → `DISPATCHED`

* **Table State:** `AVAILABLE` → `OCCUPIED` → `AWAITING CLEANUP` → `AVAILABLE`



* **Role-Based Workflows:** Tailored interfaces for Managers, Kitchen Staff, Service Staff, Cashiers, and Customers.



---

## 📂 Repository Structure

This project is organized as a monorepo containing the customer app, management console/KDS, and backend service:

```text
mezflow/
├── .github/
│   └── workflows/            # GitHub Actions CI/CD pipelines
├── docs/                     # SRS, architecture, DB ER diagram & API specs
├── apps/
│   ├── web-customer/         # Customer PWA (Next.js)
│   ├── web-admin/            # Management Console & KDS (Next.js)
│   └── backend-api/          # REST & WebSocket Engine (FastAPI)
│       ├── app/
│       │   ├── api/v1/       # API endpoints (auth, menu, tables, orders)
│       │   ├── core/         # Config, security (JWT), DB sessions
│       │   ├── models/       # Database ORM models
│       │   ├── schemas/      # Pydantic request/response schemas
│       │   └── services/     # Business logic & WebSocket manager
│       ├── alembic/          # Database migration scripts
│       └── tests/            # Pytest suite
├── docker-compose.yml        # PostgreSQL & Redis container configuration
└── README.md

```

---

## ⚡ Quickstart Setup Guide

### Prerequisites

* **Node.js** (v18 or higher)
* **Python** (v3.11 or higher)
* **Docker & Docker Compose**

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/mezflow.git
cd mezflow

```

### 2. Start Database (PostgreSQL)

```bash
docker-compose up -d postgres

```

### 3. Backend Setup (FastAPI)

```bash
cd apps/backend-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start backend server
uvicorn app.main:app --reload --port 8000

```

The API documentation will be available at `http://localhost:8000/docs`.

### 4. Frontend Setup (Next.js)

```bash
# Setup Customer PWA
cd ../web-customer
npm install
npm run dev -- -p 3000

# Setup Management Console & KDS (in a new terminal)
cd ../web-admin
npm install
npm run dev -- -p 3001

```

---

## 🗺 Development Roadmap

* [x] **Phase 1 (25% Milestone):** System Specs, Database Migrations, Auth/RBAC Engine, Management Console Menu CRUD, Table QR Code Generator, Customer Menu PWA.


* [ ] **Phase 2 (50% Milestone):** Collaborative Multi-Diner Table Session & Cart, Billing Requests, Cash/Online Checkout Integration.


* [ ] **Phase 3 (75% Milestone):** WebSocket Real-Time Synchronization, Single-Screen KDS, Preparation Timer & Delay Detection.


* [ ] **Phase 4 (100% Milestone):** Grounded AI Dish Explanation Module, Table Cleanup Lifecycle, Analytics Dashboard, Usability & Load Testing.



---

## 👥 Authors & Team Structure


* **Sheikh Muhammad Khizar** — Full-Stack Developer (Auth, Billing, AI Module, Management Console)


* **Talha Mumtaz** — Backend Developer (Database Design, Real-Time WebSockets, KDS, Delay Tracking)


* **Syed Sail Haider Gardezi** — Frontend Developer (Customer PWA, Collaborative Ordering, Table Lifecycle UI)
