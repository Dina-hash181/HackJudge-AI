# DOGFOOD Architecture Specification

> **Platform Tagline**: *"Build the platform that will judge you."*

## 1. System Architecture Overview

The DOGFOOD platform is designed as an autonomous, self-contained hackathon management and judging platform that runs with **zero external or cloud dependencies**. Built with FastAPI, SQLite3, and Vanilla ES6/CSS, the entire platform boots with a single command (`docker compose up` or `python main.py`) and is immediately operational offline.

```
+-------------------------------------------------------------------------+
|                              CLIENT TIER                                |
|  - Modern Dark Cyber Dashboard (SPA / SSR Gallery at /projects)         |
|  - Role Switcher Bar (Organizer, Judge A, Judge B, Participant, Guest)  |
|  - Client State Router (Overview, Gallery, Participant, Judge, Admin)   |
|  - Interactive Multi-Criterion Range Sliders, Modals & Print Certs      |
|  - AI Evaluation Inspector (Scores, Reasoning, Strengths, Gaps)        |
+------------------------------------+------------------------------------+
                                     | HTTP REST & Cookie/Bearer Session
                                     v
+-------------------------------------------------------------------------+
|                           APPLICATION SERVER                            |
|                            (FastAPI / Uvicorn)                          |
|                                                                         |
|  [Security & Auth Subsystem]                                            |
|   - Session Token Manager (Cookie: session=<token>, Bearer <token>)     |
|   - PBKDF2-HMAC-SHA256 Salted Password Hashing                          |
|   - Strict Server-Side Role-Based Access Control (RBAC)                 |
|   - Strict Role Isolation: Peer Judge Score Obfuscation & Rejection     |
|                                                                         |
|  [Lifecycle Engine]                                                     |
|   - Team Invitation Code Generator                                      |
|   - Submissions Deadline Guard (Reject late submissions on closed events)|
|   - Eligibility Review Matrix (Approve / Reject / Changes Requested)    |
|   - Smart Track-Affinity Judge Load Balancer                            |
|                                                                         |
|  [AI-Assisted Judging Engine]                                           |
|   - Multi-Dimension Submission Analyzer (Tech, Innovation, Impact)      |
|   - Structured Insight Extraction (Strengths, Improvements, Concerns)   |
|   - Criteria-Level Reasoning Generator & Validation                     |
|                                                                         |
|  [Judging & Scoring Engine]                                             |
|   - Weighted Multi-Criterion Rubric Aggregator                          |
|   - Cross-Judge Z-Score Normalization Engine                            |
|   - Transparent Human-AI Score Blending Formula                         |
|   - Divergence Flagging (|AI - Human| >= 1.0)                           |
|   - Judge Strictness/Leniency Bias Calibration Inspector                |
|   - Cryptographic Certificate Issuance & Validation                     |
+------------------------------------+------------------------------------+
                                     | Direct Relational SQL Queries
                                     v
+-------------------------------------------------------------------------+
|                              DATABASE                                   |
|                         (Embedded SQLite 3)                             |
|  - users, sessions, events, tracks, judges, teams, team_members,        |
|    projects, criteria, judge_assignments, scores, criterion_scores,     |
|    ai_evaluations, ai_criterion_scores, audit_logs, certificates        |
+-------------------------------------------------------------------------+
```

---

## 2. Frontend / Backend Interaction

The web application functions as an integrated single-page dashboard with server-side rendered initial project cards:
1. **SSR Initial Rendering for Compatibility**: The `/projects` route server-renders the initial set of fixture project cards into the DOM. This ensures that non-JS crawlers, automated acceptance testers (`run.py`), and curl commands immediately receive HTTP 200 and discover fixture titles (e.g. `Glass Signal`, `Small Meadow`), while web browsers hydrate the layout into a responsive dashboard.
2. **REST API Client (`app.js`)**: All lifecycle mutations (team creation, teammate invitations, project drafts, score submissions, eligibility reviews, certificate generation) communicate via asynchronous JSON REST endpoints (`/api/*`).
3. **Session Token Propagation**: The client automatically carries the session via standard `Cookie: session=<token>` and supports manual `Authorization: Bearer <token>` headers.
4. **Instant Multi-Role Switcher**: Designed specifically for hackathon evaluators, a top-bar switcher allows 1-click swapping between:
   - **Organizer** (`org_7f2a`): Full administrative command, eligibility, judge assignment, and CSV export.
   - **Judge A** (`jdg_a_91bc`, Tomas Varga): Evaluating assigned track projects, entering rubric scores.
   - **Judge B** (`jdg_b_44de`, Wei Lindqvist): Peer judge testing role isolation.
   - **Participant** (`prt_2e88`, Ada Okonkwo): Team Nightshift project submitter.
   - **Guest / Visitor**: Unauthenticated public browsing.

---

## 3. Database Schema

The relational schema in `src/database.py` enforces relational integrity using SQLite Foreign Keys:

- **`users`**: User identities, roles (`admin`, `organizer`, `judge`, `participant`), salted password hashes.
- **`sessions`**: Active tokens mapped to user accounts with timestamps.
- **`events`**: Event metadata, submission deadline (`submissions_close`), archive and publication flags.
- **`tracks`**: Challenge categories (e.g., *Developer Tools*, *Accessibility*, *Climate*).
- **`judges`**: Judge profile records, track affinities, and user linkage.
- **`teams`**: Teams, unique uppercase invite codes (e.g. `INV-TM_01-NIG`), leader foreign key.
- **`team_members`**: Membership table supporting multi-user teams and role delegation.
- **`projects`**: Submissions linked to team and track, containing title, summary, problem statement, description, technologies, repo URL, demo URL, and eligibility status.
- **`criteria`**: Configurable evaluation criteria keys, weights, and max scores.
- **`judge_assignments`**: Explicit many-to-many matrix matching judges to projects.
- **`scores`**: Judge evaluation totals, comments, and submission timestamps.
- **`criterion_scores`**: Normalized breakdown of scores per rubric criterion.
- **`audit_logs`**: Tamper-evident ledger recording all score updates, administrative actions, and configuration changes.
- **`certificates`**: Publicly verifiable certificates with alphanumeric verification codes.

---

## 4. Authentication Flow

1. **Local Authentication**: No third-party OAuth or cloud auth service is used.
2. **Password Verification**: Passwords are saved with 16 bytes of cryptographically secure salt using `hashlib.pbkdf2_hmac` with 100,000 SHA-256 iterations:
   $$\text{Hash} = \text{PBKDF2}_{\text{SHA256}}(\text{password}, \text{salt}, 100000)$$
3. **Session Token Creation**: Upon successful login, a 192-bit secure hex token (`secrets.token_hex(24)`) is generated and inserted into `sessions`.
4. **Cookie & Header Extraction**: The backend auth dependency inspects:
   - `request.cookies.get("session")`
   - Explicit `Cookie: session=<token>` header
   - `Authorization: Bearer <token>`
   - Query parameter `?token=<token>`

---

## 5. Authorization & Role-Based Access Control (RBAC)

Authorization is strictly enforced in backend route dependencies (`src/auth.py`), never solely by hiding UI buttons:

| Endpoint | Guest | Participant | Judge | Organizer / Admin |
| :--- | :---: | :---: | :---: | :---: |
| `GET /projects` | Allowed (200) | Allowed (200) | Allowed (200) | Allowed (200) |
| `POST /projects/new` | 401 | 403 (if closed) | 403 | Allowed |
| `GET /api/participant/*` | 401 | Allowed (200) | 403 | Allowed |
| `GET /api/judge/scores` | 401 | 403 Forbidden | Own Scores (200) | Allowed (200) |
| `GET /api/judge/scores?judge=peer` | 401 | 403 Forbidden | **403 Forbidden** | Allowed (200) |
| `POST /api/judge/evaluate` | 401 | 403 Forbidden | Assigned Only | Allowed |
| `POST /api/admin/*` | 401 | 403 Forbidden | 403 Forbidden | Allowed (200) |
| `GET /api/export.csv` | 401 | 403 Forbidden | 403 Forbidden | **Allowed (200)** |

---

## 6. Judging & Role Isolation Workflow

### Peer Score Isolation
A common vulnerability in hackathon platforms is exposing peer judge reviews via API parameters (e.g. `/api/judge/scores?judge=judge_a`). In DOGFOOD:
- If Judge B sends a request to inspect Judge A's scores, the backend explicitly verifies `target_judge_id == current_user_judge_id`.
- If they do not match and the user is not an organizer, the server refuses with **HTTP 403 Forbidden**.
- Scores are never leaked into response bodies or templates.

---

## 7. Scoring & Normalization Algorithm

Raw averages are inherently vulnerable to judge calibration discrepancies (e.g. one judge scoring all projects 2/5 and another scoring 5/5). DOGFOOD implements a **Cross-Judge Z-Score Normalization Engine**:

1. **Judge Mean & Standard Deviation**:
   $$\mu_j = \frac{1}{N_j} \sum_{i=1}^{N_j} s_{ij}, \quad \sigma_j = \sqrt{\frac{1}{N_j} \sum_{i=1}^{N_j} (s_{ij} - \mu_j)^2}$$
2. **Standardization**:
   $$z_{ij} = \frac{s_{ij} - \mu_j}{\sigma_j} \quad (\text{for } \sigma_j > 0.001)$$
3. **Rescaling to Global Scale**:
   $$\hat{s}_{ij} = \mu_{\text{global}} + z_{ij} \times \sigma_{\text{global}}$$
   $$\text{Final Project Score} = \frac{1}{K} \sum_{j=1}^K \hat{s}_{ij}$$

Full mathematical derivation, edge cases, and proofs are documented in `JUDGING.md`.

---

## 8. Data Flow Lifecycle

```
[Registration / Team Formation]
       |
       v
[Project Submission Draft & Finalize]
       |
       v (Deadline Guard: submissions_close)
[Eligibility Review by Organizer]
       |
       v
[Smart Track-Affinity Judge Assignment]
       |
       v
[Isolated Judge Evaluation on Weighted Rubrics]
       |
       v
[Audit Logging & Cross-Judge Z-Score Normalization]
       |
       v
[Public Leaderboard, CSV Export & Certificate Issuance]
       |
       v
[Immutable Event Archival]
```
