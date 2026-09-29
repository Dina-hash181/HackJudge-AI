# HackJudge AI · Autonomous Hackathon Management & Judging Platform

> *"Build the platform that will judge you."*

**HackJudge AI** is an open-source, self-contained hackathon lifecycle management and autonomous judging platform. Built for the DOGFOOD 2026 specification, it runs entirely offline on localhost with **zero external cloud dependencies, zero proprietary API keys, and zero hosted services**.

[![License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](LICENSE)
[![Acceptance Status](https://img.shields.io/badge/Acceptance-Verified%20T1%20T2-00E5D0.svg)](acceptance-report.txt)
[![Python: 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![Docker: Ready](https://img.shields.io/badge/Docker-compose%20ready-2496ED.svg)](docker-compose.yml)
[![Open Source: OSI Approved](https://img.shields.io/badge/OSI-Approved%20License-green.svg)](https://opensource.org/licenses/MIT)


---

## 🌐 Live Demos & Public Links

- **Live Netlify Web App**: [https://idyllic-sprinkles-b27475.netlify.app](https://idyllic-sprinkles-b27475.netlify.app) *(Password: `My-Drop-Site`)*
- **Live Cloudflare Public Tunnel**: [https://budget-dean-tickets-barnes.trycloudflare.com](https://budget-dean-tickets-barnes.trycloudflare.com)
- **Official GitHub Repository**: [https://github.com/Dina-hash181/HackJudge-AI](https://github.com/Dina-hash181/HackJudge-AI)

---
## 🏆 Dogfood 2026 Specification Compliance

| Requirement | Implementation & Proof | Status |
| :--- | :--- | :--- |
| **Repository is Public** | Clean open repository layout with standard `.gitignore`, `.dockerignore`, and modular source code. | ✅ **Public** |
| **Real Working Code** | Real FastAPI + SQLite + JavaScript client. 41 real project records, active sessions, and database migrations. | ✅ **Verified** |
| **Zero Hosted Dependencies** | Self-contained local auth, embedded SQLite relational storage (WAL mode), deterministic local AI judge. | ✅ **Offline** |
| **OSI-Approved License** | Permissive, official **MIT License** included in root [`LICENSE`](LICENSE). | ✅ **OSI Approved** |
| **`docker compose up`** | Production-ready [`Dockerfile`](Dockerfile) and [`docker-compose.yml`](docker-compose.yml) binding port `8080`. | ✅ **Supported** |
| **Acceptance Checker** | Official `python run.py .dogfood.toml` passes **7 out of 7 checks** (`claimed T1 T2, verified T1 T2`). | ✅ **7/7 PASS** |

---

## 🚀 How to Run the Platform

You can run HackJudge AI locally either via Python directly or using Docker Compose.

### Option 1: Run with Python Directly (Recommended & Instant)

**Prerequisites**: Python 3.10 or newer (tested on 3.10, 3.11, 3.12).

```bash
# 1. Clone the repository
git clone https://github.com/Dina-hash181/HackJudge-AI.git
cd HackJudge-AI

# 2. (Optional) Create and activate a virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux / macOS:
source venv/bin/activate

# 3. Install lightweight dependencies (FastAPI, Uvicorn, Pydantic)
pip install -r requirements.txt

# 4. Launch the platform (automatically initializes SQLite schema & seeds 41 projects)
python main.py
```

Open **[http://localhost:8080](http://localhost:8080)** in your browser.

---

### Option 2: Run with Docker Compose

If you have Docker installed, you can start the platform with a single command:

```bash
# Build the container and start the service
docker compose up --build

# Or run in detached background mode:
docker compose up -d
```

The portal will be live immediately at **[http://localhost:8080](http://localhost:8080)**.

To stop the container:
```bash
docker compose down
```

---

## 🧪 Running the Verification Test Suites

### 1. DOGFOOD 2026 Official Acceptance Runner

Run the official spec verification script against the running portal:

```bash
python run.py .dogfood.toml
```

**Verified Output (`acceptance-report.txt`)**:
```
DOGFOOD 2026 acceptance report
portal: http://localhost:8080
claimed: T1 T2
fixtures: fixtures.json

T1  gallery is public ................. PASS
T1  project from fixtures shown ....... PASS
T1  closed event refuses submissions .. PASS
T2  judge sees own scores ............. PASS
T2  judge cannot see peer scores ...... PASS
T2  participant blocked ............... PASS
T2  csv export works .................. PASS

claimed T1 T2, verified T1 T2
```

### 2. Built-in Automated Unit Tests

Run the full Python unit test suite:

```bash
python -m unittest discover tests
```

*Results: 9 tests passing covering API authentication, RBAC, submission deadlines, peer-score isolation, and AI evaluation.*

---

## 🔑 Pre-Seeded Test Credentials & Fixed Sessions

For effortless manual evaluation and testing, the application includes a **1-click Role Switcher** in the top navigation bar, as well as seeded user credentials:

| Role | Username / Identifier | Default Password | Fixed Session Cookie (`.dogfood.toml`) | Permissions & Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **👑 Organizer / Admin** | `organizer` | `adminpassword` or `dogfood2026` | `Cookie: session=org_7f2a` | Full administration, project eligibility toggles, auto-assignment, CSV export |
| **⚖️ Judge A** | `judge_a` (Tomas Varga) | `judgepassword` or `dogfood2026` | `Cookie: session=jdg_a_91bc` | Evaluation of assigned projects, multi-criterion scoring |
| **⚖️ Judge B** | `judge_b` (Wei Lindqvist) | `judgepassword` or `dogfood2026` | `Cookie: session=jdg_b_44de` | Testing role isolation against peer score access |
| **🚀 Participant** | `participant` (Ada Okonkwo) | `participantpassword` or `dogfood2026` | `Cookie: session=prt_2e88` | Team Nightshift management, submission editing, invite codes |
| **👤 Guest / Visitor** | Public / Unauthenticated | N/A | None | Browse public gallery, view code repositories, launch interactive demo sandboxes |

*Note: New accounts can also be created dynamically via the "Create Account / Sign Up" tab in the authentication modal.*

---

## 🏗️ Core Architecture & Features

### 1. Zero-Cloud Local Authentication & RBAC
- Local session tokens stored in embedded SQLite `sessions` table.
- PBKDF2-HMAC-SHA256 password hashing with cryptographic salt.
- Server-side role enforcement: non-organizers attempting CSV exports receive HTTP 403; judges querying peer scores receive HTTP 403; submissions past deadline receive HTTP 403.

### 2. Public Project Gallery & Multi-File Repository Explorer
- Public route `/projects` displaying all 41 hackathon projects.
- In-app **Code Repository Explorer** (`💻 View Code`): evaluators can browse real multi-file code trees (Python, TypeScript, C++, configs, unit tests) without leaving the application.
- **Domain-Tailored Codebases**: Distinct architectures for Security, Accessibility, Education, Data & Analytics, DevTools, Health, Open Hardware, and Climate.

### 3. Live Interactive Demo Sandboxes
- In-app **Interactive Demo Sandbox** (`🚀 Live Demo`): Evaluators can interact with working domain widgets:
  - *Security*: Live encryption input, zero-knowledge verification proof, threat detector.
  - *Accessibility*: Interactive WCAG 2.2 AAA color contrast tester and speech synthesis simulator.
  - *Health*: Live pulsing ECG cardiac telemetry monitor (BPM, SpO2) and arrhythmia alert trigger.
  - *Data & Analytics*: Real-time stream telemetry slider with Z-score anomaly alarm.
  - *DevTools*: Live AST optimizer and 50,000-iteration micro-benchmarking engine.
  - *Education*: Interactive adaptive challenge solver with concept mastery scoring.
  - *Climate*: Marginal carbon accounting calculator and solar forecast curve.
  - *Open Hardware*: Virtual GPIO pin 14 relay toggle switch with live LED indicators.

### 4. HackJudge AI Evaluation Engine
- Deterministic heuristic analysis evaluating:
  - Technical Implementation (25%)
  - Innovation & Novelty (20%)
  - Problem Relevance (20%)
  - Potential Impact (20%)
  - Usability & Polish (15%)
- Comprehensive reasoning summary, identified strengths, actionable improvements, potential risks, and missing information gaps.
- **Human Safeguards**: AI serves strictly as an assistant; human judging integrity is preserved. Highlights divergence when $|AI - Human| \ge 1.0$.

### 5. Mathematical Score Normalization (Z-Score)
- Cross-judge Z-Score calibration adjusting for strict vs lenient reviewer biases:
  $$Z = \frac{x - \mu}{\sigma}, \quad \text{Score}_{\text{norm}} = 3.0 + (Z \times 1.0)$$
- Blended final score weighting (default: 80% Human / 20% AI, customizable by organizers).

### 6. Official Verifiable Certificates
- Generate cryptographic certificates for participants, judges, and winners.
- Unique verification codes (e.g. `CERT-DF-2026-WIN-XXXX`).
- High-fidelity printable / PDF preview layout.

---

## 📁 Repository File Structure

```
.
├── .dogfood.toml              # Dogfood spec route & auth session configuration
├── acceptance-report.txt       # Official run.py verified receipt (7/7 PASS)
├── fixtures.json              # Standard 41-project event fixture dataset
├── run.py                     # Official DOGFOOD 2026 acceptance test runner
├── main.py                    # Root FastAPI application entry point
├── seed.py                    # Database seed execution script
├── requirements.txt           # Python package dependencies (zero cloud)
├── Dockerfile                 # Multi-stage production container specification
├── docker-compose.yml         # One-command Docker Compose orchestration
├── .dockerignore              # Clean container build exclusions
├── .gitignore                 # Git ignore rules
├── LICENSE                    # OSI-Approved MIT License
├── README.md                  # Comprehensive setup & user manual
├── ARCHITECTURE.md            # Detailed system architecture & RBAC model
├── AI_JUDGING.md              # AI judging heuristics, prompts, & safeguards
├── DATA-MODEL.md              # SQLite schema, tables, and relational pipelines
├── JUDGING.md                 # Mathematical normalization proof & scoring rubrics
├── tests/
│   ├── __init__.py
│   ├── test_api.py            # API endpoint, RBAC, and deadline tests
│   └── test_ai_judging.py     # AI evaluation & scoring test cases
└── src/
    ├── __init__.py
    ├── main.py                # FastAPI app factory & lifespan
    ├── config.py              # Environment configuration & constants
    ├── database.py            # SQLite connection manager with WAL mode
    ├── auth.py                # Password hashing, session tokens, RBAC guards
    ├── scoring.py             # Z-Score normalization & leaderboard engine
    ├── ai_judging.py          # HackJudge AI analytical engine (HackJudge-AI-v2.5)
    ├── project_assets.py      # Domain-specific multi-file codebases & demo states
    ├── seed_data.py           # Ingestion logic for fixtures.json
    ├── routes/
    │   ├── auth_routes.py     # Sign In, Sign Up, role switcher
    │   ├── participant_routes.py # Teams, invites, submission deadline guard
    │   ├── judge_routes.py    # Assigned projects, scoring, peer isolation
    │   ├── admin_routes.py    # Overview, eligibility, auto-assignment
    │   ├── public_routes.py   # Gallery, results, certificates, CSV export
    │   └── ai_routes.py       # HackJudge AI console, batch evaluations
    ├── static/
    │   ├── css/style.css      # Modern white light aesthetic with emerald accents
    │   └── js/app.js          # Interactive client application
    └── templates/
        └── index.html         # Unified single-page responsive dashboard
```

---

## 📜 License

This project is licensed under the **MIT License** — an open-source, OSI-approved license. See the [`LICENSE`](LICENSE) file for complete terms.
