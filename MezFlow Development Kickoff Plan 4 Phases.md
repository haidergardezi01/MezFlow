# MezFlow: Development Kickoff Plan

**Project:** MezFlow, a Real-Time Restaurant Dining and Kitchen Operations Management System **Team:** Sheikh Muhammad Khizar, Talha Mumtaz, Syed Sail Haider Gardezi **Supervisor:** Muhammad Farooq, SZABIST Islamabad **Methodology:** Agile Scrum, two-week sprints **Implementation window:** 16 weeks (4 phases x 4 weeks, two sprints each)

---

## 1. Purpose of This Document

This document turns the approved MezFlow proposal and README into an actionable plan for starting development. It splits the work into four phases that match the 25%, 50%, 75% and 100% milestones in the README roadmap. Each phase lists its goal, the modules involved, concrete tasks per team member, deliverables, exit criteria and risks.

## 2. Guiding Principles

- **Vertical slices first.** Each phase ends with something demoable end to end, not isolated layers.
- **Server-authoritative state.** Cart, order, table and price logic live on the backend. Clients never decide truth.
- **Two independent state machines.** Order state (New, Confirmed, Preparing, Ready, Dispatched) and table state (Available, Occupied, Awaiting Cleanup, Available) are never coupled in code.
- **Multi-tenant from day one.** Every table carries a restaurant ID, with Row-Level Security applied at the database layer.
- **Audit everything that matters.** State changes, price overrides, payments and menu edits write to an event log from the first migration.
- **MVP-first module order.** Out-of-scope items stay out unless the supervisor approves a change.

## 3. Team Ownership

| Member | Primary role | Modules owned |
| --- | --- | --- |
| Sheikh Muhammad Khizar | Full-stack, backend architecture, QA | M1 Identity and Access, M5 Order Lifecycle and Real-Time Sync, M8 Billing, M7 AI Dish Explanation, M10 Management Console, M12 Analytics |
| Syed Sail Haider Gardezi | Frontend, customer UX | M2 Digital Menu and QR, M3 Collaborative Ordering, M9 Table Lifecycle |
| Talha Mumtaz | Backend, real-time, database | M4 Kitchen Display System, M6 Prep-Time Tracking, M11 Service Requests and Notifications, database design |

Shared by all: requirements, SRS, design, integration, usability trial, documentation.

Note: the proposal's team table lists Talha for database design and the README does too, while the proposal's work distribution gives Khizar the backend architecture. Treat Talha as schema owner and Khizar as API architecture owner, and confirm this in the first meeting.

## 4. Phase Overview

| Phase | Weeks | Milestone | Theme | Modules |
| --- | --- | --- | --- | --- |
| 1 | 1-4 | 25% | Foundation: specs, database, auth, menu, QR | M1, M2, M10 (menu and table CRUD) |
| 2 | 5-8 | 50% | Ordering: shared table cart and billing | M3, M8, M10 (extended) |
| 3 | 9-12 | 75% | Real-time: WebSockets, KDS, delay detection | M4, M5, M6, M11 |
| 4 | 13-16 | 100% | Intelligence and polish: AI, table cleanup, analytics, testing | M7, M9, M12, hardening |

---

## 5. Phase 1: Foundation (Weeks 1-4, 25% Milestone)

### Goal

A manager can log in, build a menu and tables, print table QR codes, and a customer can open the live menu from a QR scan on a phone.

### Sprint 1 (Weeks 1-2): Setup and Design

**Whole team**

- Create the GitHub monorepo with the structure from the README: `apps/web-customer`, `apps/web-admin`, `apps/backend-api`, `docs`, `.github/workflows`.
- Agree on branching (main, develop, feature branches), pull request rules, commit conventions and code review (at least one reviewer per PR).
- Write the SRS: functional requirements per module, non-functional targets (first load under 3 seconds, 2-second real-time propagation, 50 concurrent WebSocket connections).
- Build the product backlog in a board (GitHub Projects) with user stories for all twelve modules, prioritized MVP-first.
- Hold short interviews with two or three restaurant owners or staff to validate the KDS filters and the table flow.

**Talha**

- Design the ER diagram: restaurant, table, table\_session, diner, menu\_category, menu\_item, modifier, order, order\_item, payment, event\_log, user, role.
- Write the first SQLModel models and Alembic migration.
- Set up `docker-compose.yml` with PostgreSQL. Decide now whether Redis is needed: the README mentions it, but the proposal's architecture does not require it. Default to PostgreSQL only and add Redis in Phase 3 only if WebSocket fan-out needs it.

**Khizar**

- Scaffold the FastAPI app: `api/v1`, `core`, `models`, `schemas`, `services`.
- Configure settings management, DB session handling, structured logging and CORS.
- Set up GitHub Actions: lint, type-check and pytest on every pull request.

**Sail**

- Create Figma wireframes: customer menu, item detail with modifiers, cart screens and the manager console layout.
- Scaffold both Next.js apps with TypeScript, Tailwind CSS and a shared design token file.
- Configure PWA basics: manifest, service worker shell, mobile-first layout.

### Sprint 2 (Weeks 3-4): Auth, Menu, QR

**Khizar (M1)**

- Implement sign-up and login by phone or e-mail with OTP, bcrypt hashing and JWT access and refresh tokens.
- Implement RBAC with five roles (Customer, Kitchen Staff, Service Staff, Cashier, Manager) as a reusable dependency.
- Write the audit-log writer and apply it to staff actions.
- Use a stubbed OTP provider (console or e-mail) for development to avoid SMS cost.

**Talha**

- Apply tenant isolation: restaurant ID on every tenant table and Postgres RLS policies, with tests proving cross-tenant reads fail.
- Build menu API endpoints: categories, items, modifiers, availability, price, expected prep time, kitchen category mapping.
- Build table API endpoints and the QR token generator. Use a signed, non-guessable table token rather than a raw table ID.

**Sail (M2)**

- Build the management console menu CRUD screens and the table and QR generator screen (downloadable and printable QR).
- Build the customer menu PWA: QR landing route that resolves the table token, category tabs, item cards, modifier picker.
- Measure first-load performance on a throttled mobile connection against the 3-second target.

### Deliverables

- Running monorepo with CI passing.
- SRS v1 and design document draft (architecture, ER diagram, API outline).
- Auth and RBAC, menu and table CRUD, QR generation, customer menu PWA.
- Seed script with one demo restaurant, 10 tables and about 30 menu items.

### Exit Criteria

- A manager creates a menu item, and it appears in the customer PWA after scanning a table QR code.
- RBAC test suite proves each role can reach only its own endpoints.
- RLS tests prove restaurant A cannot read restaurant B data.
- CI is green; demo accepted by the supervisor.

### Risks

- OTP delivery cost or delay: use a stub provider and swap in a real one late.
- Schema churn: freeze the core tables by the end of Sprint 1 and change them only through migrations.

---

## 6. Phase 2: Collaborative Ordering and Billing (Weeks 5-8, 50% Milestone)

### Goal

Several diners at one table build a single shared cart, submit one order, request the bill, and a cashier closes the session.

### Sprint 3 (Weeks 5-6): Table Sessions and Shared Cart

**Talha (backend foundations)**

- Implement the table session model: the first scan opens a session, later scans from the same table join it, and a session code expires on closure.
- Implement the diner identity model: anonymous diner IDs with an optional display name, stored per session.
- Implement the cart with per-item diner attribution and server-authoritative versioning (a version number on every cart mutation).

**Sail (M3)**

- Build the shared cart UI: add, edit and remove items, diner badges on each item, live total.
- Use optimistic UI that reconciles against the server version. Show a clear indicator when the connection is lost.
- Build the order submit flow: one confirm step, then a locked cart and an order confirmation screen.

**Khizar**

- Implement a first, minimal WebSocket channel for the cart only (subscribe to table session, broadcast cart changes). This is built early as a spike so the harder Phase 3 work starts de-risked.
- Add server-side price validation: the backend recomputes every price from the menu and ignores client-sent prices.

### Sprint 4 (Weeks 7-8): Order Creation and Billing

**Khizar (M8)**

- Implement order creation from a submitted cart: one order per table session submission, with order items carrying diner attribution, modifiers and kitchen category.
- Implement the bill: itemized, with taxes and service charge from restaurant configuration.
- Implement the bill request, cashier review, cash or card payment record and session closure with audit entries. Closing the session must not touch table state.

**Sail**

- Build the customer bill screen (request bill, view itemized total, see paid status).
- Build the cashier screen in the admin app: list of bill requests, bill detail, mark as paid.

**Talha**

- Add the order and payment tables' constraints, indexes and the event-log entries for each transition.
- Write concurrency tests: two diners adding the same item simultaneously, two submits racing, and duplicate payment attempts.

### Deliverables

- Shared table session and cart with live updates between at least two phones.
- Order creation, bill request, cashier payment and session closure.
- API specification (OpenAPI) updated for sessions, cart, orders and billing.
- Test suite covering price validation and cart concurrency.

### Exit Criteria

- Two or more phones scan the same QR, see each other's items in under 2 seconds and submit one order.
- A tampered client price is rejected or overwritten by the server in a test.
- Paying the bill closes the session and leaves the table state unchanged.
- Demo to the supervisor, followed by feedback folded into the backlog.

### Risks

- Lost updates in the shared cart: mitigated with server versioning and full-state resync on reconnect.
- Payment integration scope: keep to cash and manual card recording for the FYP, with online gateway as a stretch item behind an interface.

---

## 7. Phase 3: Real-Time Kitchen Operations (Weeks 9-12, 75% Milestone)

### Goal

Submitted orders appear instantly on a single-screen KDS, move through the order lifecycle, and the customer sees live status. Late dishes are flagged automatically.

### Sprint 5 (Weeks 9-10): Real-Time Layer and KDS

**Khizar (M5)**

- Generalize the WebSocket manager into rooms: per table session, per restaurant kitchen, per restaurant management.
- Authenticate WebSocket connections with JWT or a session token and enforce tenant and role checks on subscribe.
- Implement the order state machine as a single service: legal transitions only, each one logged, each one emitting an event.
- Add reconnect support: sequence numbers or versions on events, plus a REST snapshot endpoint for resync.

**Talha (M4)**

- Build the KDS data API: active orders with items, modifiers, table number, status and elapsed time.
- Implement kitchen category routing so a customer-facing category such as Main Course maps to a station such as Hot Kitchen.
- Write a load-test scaffold with Locust that simulates many tables ordering.

**Sail**

- Build the KDS screen in the admin app: independent order cards, status filters (New, Preparing, Ready, Delayed), category filters (Grill, Fry, Hot Kitchen, Beverage).
- Add large touch-friendly controls for tablet use, with one-tap status advance and an undo window.
- Build the live order status tracker in the customer PWA.

### Sprint 6 (Weeks 11-12): Delay Detection and Notifications

**Talha (M6)**

- Implement per-item expected preparation time, with timers starting when an order enters Preparing.
- Implement a background scheduler that flags delayed orders and broadcasts the delay event. Make delays derived from timestamps, so they remain correct after a server restart.
- Show elapsed time and a delay badge on the KDS cards.

**Talha and Sail (M11)**

- Build service requests (call waiter, water refill, other) and the service staff queue sorted by table and wait time.
- Add notifications: in-app first, then web push for order status, bill readiness and request acknowledgement.

**Khizar**

- Harden the real-time layer: backpressure, ping/pong heartbeat, connection limits and error events.
- Add integration tests for the full flow: submit, confirm, prepare, ready, dispatch, with simulated clients.

### Deliverables

- Real-time order flow across the customer app, KDS and management console.
- Delay detection with configurable timers, service requests and notifications.
- Load-test report v1.

### Exit Criteria

- Status changes reach all connected clients within 2 seconds under normal conditions.
- 10 simultaneous table orders in a 2-minute window display correctly without cross-order interference.
- 50 concurrent WebSocket connections run without state corruption.
- Illegal order transitions are rejected by tests.

### Risks

- Unstable restaurant Wi-Fi: automatic reconnect with resync, plus REST fallback for critical reads.
- Kitchen staff resistance: run an early on-site or mock walkthrough of the KDS and adjust filters before Phase 4.

---

## 8. Phase 4: Intelligence, Table Lifecycle and Release (Weeks 13-16, 100% Milestone)

### Goal

Complete the remaining modules, harden the system, evaluate it against the proposal's targets and package everything for final submission.

### Sprint 7 (Weeks 13-14): AI, Table Cleanup and Analytics

**Khizar (M7)**

- Build the Explain This Dish service. The prompt receives only the restaurant-supplied structured fields (ingredients, flavor, texture, heat level, portion size) and instructs the model to state nothing beyond them.
- Support English and Urdu output, chosen from the diner's language preference.
- Add manager controls for which fields are supplied per dish, and a manual review or approve step before an explanation is published.
- Cache generated explanations and invalidate them when the dish data changes. Add rate limits and a safe fallback to the static description on model failure.

**Sail (M9)**

- Implement the table state machine UI: Available, Occupied, Awaiting Cleanup, Available.
- Build the live table status board for service staff and managers, with a one-tap Confirm Cleaned action.
- Verify the rule that payment moves the table to Awaiting Cleanup, never directly to Available.

**Khizar and Talha (M12)**

- Build the analytics dashboard: orders, average preparation time and delayed-order rate by date and category, using event-log aggregates.
- Add exportable reports (CSV at minimum) and an audit-trail viewer.

### Sprint 8 (Weeks 15-16): Testing, Hardening and Documentation

**Whole team**

- Run the usability trial with at least 10 participants, including non-technical users, and compute the System Usability Scale score (target 70 or above). Fix the top issues found.
- Run final load tests with Locust (50 or more WebSocket connections, 10 simultaneous table orders) and record results.
- Conduct the AI grounding review: manually check a sample of explanations in both languages for any fact not present in the supplied data.
- Security pass: dependency audit, rate limiting, input validation, JWT expiry, RLS re-test and removal of debug endpoints.

**Talha**

- Produce Docker Compose production configuration, Nginx reverse proxy with WebSocket upgrade and TLS, and a deployment guide for a cloud VPS.

**Khizar**

- Finalize the automated test report and CI coverage numbers.

**Sail**

- Polish the UI: empty states, error states, loading states and Urdu layout checks.

### Deliverables

- All twelve modules complete and integrated.
- Final SRS, design document (architecture, ER diagram, API spec), test report, user manual and deployment manual.
- Usability trial results and load-test report.
- Deployed pilot instance and a final demo script.

### Exit Criteria

- Every objective in the proposal (Objectives 1-10) is either met or has a documented, supervisor-agreed variance.
- SUS score of 70 or above, or a documented improvement plan.
- Full workflow demo works without manual intervention: scan, shared cart, order, kitchen, serve, bill, payment, cleanup, available.

### Risks

- Scope pressure in the last sprint: freeze new features at the start of Week 15.
- AI drift: the review step and strict field-only prompting are mandatory, and fallback text is used on any failure.

---

## 9. Cross-Cutting Practices

**Testing.** Unit tests with pytest for services (state machines, price validation, RBAC), API tests with Postman collections, and Locust for load. Every pull request must pass CI.

**Definition of Done.** Code reviewed and merged, tests written and passing, API docs updated, migration included where the schema changed, feature demoed in the sprint review.

**Sprint ceremonies.** Planning on day 1, short stand-ups three times a week, a review with the supervisor at the end of each sprint, and a retrospective after the review.

**Documentation.** Update the SRS and design documents at the end of each phase so documentation never lags behind the code.

**Environments.** Local Docker Compose for development, a shared staging VPS from Phase 2 onward, and a production-like pilot instance in Phase 4.

## 10. Phase Dependency Summary

- Phase 2 depends on the auth, menu and table models from Phase 1.
- Phase 3 depends on the order and cart data model from Phase 2, and reuses the early WebSocket spike.
- Phase 4 depends on the order lifecycle (for analytics), the payment flow (for the table state machine) and complete dish data (for the AI module).

## 11. Immediate Next Steps (Week 1, Day 1 to 5)

1. Create the GitHub repository and monorepo skeleton, and invite the supervisor.
2. Set up the project board with the Phase 1 backlog and assign owners.
3. Draft the ER diagram and review it as a team before any migration is written.
4. Scaffold FastAPI, both Next.js apps and Docker Compose with PostgreSQL, and confirm everyone can run the full stack locally.
5. Schedule the first supervisor review at the end of Sprint 1.
6. Decide the open items: Redis in or out, OTP provider for development, and the final split of backend ownership between Khizar and Talha.
