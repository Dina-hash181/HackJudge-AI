# DOGFOOD AI-Assisted Judging System (The AI Judge)

> **Core Philosophy**: *"The AI Judge is an assistant and co-pilot to human evaluators, never an invisible replacement or an uninspectable black box."*

---

## 1. System Architecture & Workflow

The DOGFOOD AI Judging subsystem provides transparent, multi-dimensional automated evaluation of hackathon submissions while preserving strict human-in-the-loop integrity.

```
 [Participant Submission]
  - Title, Problem Statement, Solution Description
  - Features, Tech Stack, Repo URL, Demo URL, Video URL
            |
            v
 [Ingestion & Sanitization API]
            |
            v
 [AI Judge Analytical Engine]
   * Technical Implementation (25%)
   * Innovation & Novelty (20%)
   * Problem Relevance (20%)
   * Potential Impact (20%)
   * Usability & Polish (15%)
            |
            +-----------------------------------+
            |                                   |
            v                                   v
  [Structured Criterion Breakdown]    [Analytical Qualitative Insights]
   - Per-criterion scores (1.0 - 5.0)   - Key Strengths
   - Per-criterion reasoning text       - Actionable Areas for Improvement
   - Weighted overall AI score          - Potential Concerns & Risks
                                        - Missing Information / Evidence Gaps
            |                                   |
            +-----------------+-----------------+
                              |
                              v
       [Storage: ai_evaluations & ai_criterion_scores]
                              |
                              v
 [Human Judge Independent Scoring] <--- Isolated from AI tampering
            |
            v
 [Transparent Score Blending Engine]
   FinalScore = (HumanScore * w_human) + (AIScore * w_ai)
            |
            v
 [Divergence Alerting Engine: |AI - Human| >= 1.0]
            |
            v
 [Public Results & Verifiable Export]
```

---

## 2. Input Schema & Data Requirements

The AI Judge evaluates strictly on actual submitted data. Unverified claims outside the submission payload are treated as missing information:

```json
{
  "project_id": "prj_01",
  "title": "Glass Signal",
  "summary": "Low-latency reactive state synchronization engine.",
  "problem_statement": "Addressing high-latency synchronization and complex state validation in modern distributed setups.",
  "solution_description": "An end-to-end self-contained architecture with reactive client state, automated health heuristics, and complete local persistence without any hosted external reliance.",
  "features": "Reactive Client State, Local Offline Storage, Real-time Sync Engine, Role-Based Access Control, Automated Health Heuristics",
  "technologies": "Python, FastAPI, SQLite, WebSockets, Vanilla JS, TailwindCSS",
  "repo_url": "https://github.com/example/glass-signal",
  "demo_url": "https://demo.dogfoodhack.com/p/prj_01",
  "video_url": "https://videos.dogfoodhack.com/v/prj_01.mp4"
}
```

---

## 3. Output Schema & Data Contracts

The AI Judge emits a validated, structured contract that is parsed and validated before persistence:

```json
{
  "model_name": "Dogfood-AI-Judge-v2.0",
  "overall_score": 4.35,
  "reasoning": "Evaluated as a 4.5/5.0 technical submission with 4.1/5.0 innovation. Strong implementation signals with linked repository and cohesive technology choices.",
  "criteria": {
    "technical_implementation": {
      "score": 4.5,
      "weight": 0.25,
      "reasoning": "Provided accessible code repository. Employs cohesive tech stack (fastapi, sqlite, python). Detailed implementation breakdown provided."
    },
    "innovation": {
      "score": 4.1,
      "weight": 0.20,
      "reasoning": "Demonstrates non-trivial architecture targeting autonomous sync and reactive state engines."
    },
    "problem_relevance": {
      "score": 4.4,
      "weight": 0.20,
      "reasoning": "Articulates a concrete problem domain: 'Addressing high-latency synchronization...'. Focuses on high-leverage systems challenges."
    },
    "impact": {
      "score": 4.5,
      "weight": 0.20,
      "reasoning": "Clear solution path with broad utility for target audience. Designed for reusable adoption across external communities."
    },
    "usability": {
      "score": 4.0,
      "weight": 0.15,
      "reasoning": "Live interactive demo available for direct verification. Explicit user features cataloged."
    }
  },
  "strengths": [
    "Public code repository verifiable at https://github.com/example/glass-signal",
    "Interactive live deployment supplied for evaluators",
    "Modular technology stack utilizing fastapi, sqlite, python",
    "Clearly formulated problem statement with defined target beneficiaries"
  ],
  "improvements": [
    "Include automated performance benchmark metrics under concurrent user loads",
    "Expand documentation on partition tolerance edge cases"
  ],
  "concerns": [
    "Potential scalability constraints under heavy multi-tenant concurrency if unbounded"
  ],
  "missing_info": [
    "None. Submission payload satisfies all baseline informational requirements."
  ]
}
```

---

## 4. Evaluation Criteria & Weighting Rubric

The AI evaluation applies a normalized 5-dimension rubric:

| Dimension | Weight | Description | Scoring Indicators |
| :--- | :---: | :--- | :--- |
| **Technical Implementation** | **25%** | Code quality, architecture robustness, stack fit. | Repository link present (+0.8), modern modular stack (+0.7), detailed technical description (+0.4). |
| **Innovation & Novelty** | **20%** | Uniqueness, creative departure from standard CRUD. | Novel architecture, decentralized/autonomous logic, non-trivial algorithmic design (+0.3 to +1.3). |
| **Problem Relevance** | **20%** | Clarity of pain point, user empathy. | Concrete problem statement (+0.9), high-leverage reliability or systems focus (+0.5). |
| **Potential Impact** | **20%** | Scope of utility, feasibility of adoption. | Articulated solution (+0.8), community/industry adoption potential (+0.6). |
| **Usability & Polish** | **15%** | Accessibility, live demonstration, user UX. | Live demo URL (+1.2), walkthrough video (+0.5), feature list (+0.4). |

---

## 5. Transparent Final Score Blending Formula

The final hackathon score combines human judge evaluations and the AI assistant score using administrator-configurable weights:

$$\text{FinalScore} = (\text{HumanScore}_{\text{norm}} \times w_{\text{human}}) + (\text{AIScore} \times w_{\text{ai}})$$

### Default Weighting Configuration:
- **$w_{\text{human}} = 0.80$ (80% Weight)**: Human evaluators hold primary governing authority.
- **$w_{\text{ai}} = 0.20$ (20% Weight)**: AI assistant provides a baseline stabilizing signal across projects.

### Transparency Guarantees:
- The scoring formula is never hidden. Every row on the Leaderboard displays the exact weights used (e.g. `80% Human + 20% AI`).
- Organizers can dynamically reconfigure weights via the Admin Console (`POST /api/ai/weights`) or adjust to 100% Human / 0% AI if desired.
- All weight adjustments are recorded in `audit_logs`.

---

## 6. Score Difference & Divergence Alerting ($|\Delta| \ge 1.0$)

To ensure humans and AI cross-check each other:
1. **Delta Calculation**:
   $$\Delta = \text{AIScore} - \text{HumanScore}$$
2. **Divergence Threshold**:
   If $|\Delta| \ge 1.0$, the project is flagged as **`⚠️ DIVERGENT`** in the AI Dashboard and Admin Console.
3. **Audit Trigger**:
   Divergent reviews alert human organizers to inspect whether human judges missed key technical features or if the AI engine overrated or penalized a specific aspect.

---

## 7. Database Persistence & Audit Ledger

AI evaluations are stored in dedicated first-class relational tables in `dogfood.db`:
- **`ai_evaluations`**: `(id, project_id, model_name, overall_score, reasoning, strengths_json, improvements_json, concerns_json, missing_info_json, evaluated_at)`
- **`ai_criterion_scores`**: `(id, ai_eval_id, criterion_key, score, weight, reasoning)`
- **`audit_logs`**: Every evaluation run records user, model, project, score, and UTC timestamp.

---

## 8. Safeguards, Protections & Anti-Hallucination Controls

1. **No Direct Mutation of Human Scores**:
   The AI Judge has zero permissions to alter, overwrite, or delete human judge submissions.
2. **Zero Unrestricted Database Access**:
   The AI engine runs through typed Python methods and API endpoints. Raw SQL access is strictly forbidden.
3. **Structured Schema Validation**:
   Scores must lie within $[1.0, 5.0]$. Any out-of-bounds float or unparseable JSON is rejected before database insertion.
4. **Offline Resilience**:
   The built-in evaluation engine runs completely offline with standard Python libraries. No external cloud service or API key is required for the system to boot, evaluate submissions, and pass all acceptance tests.
