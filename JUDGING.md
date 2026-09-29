# DOGFOOD Judging, Scoring & Normalization Engine

> **Bonus Challenge Focus**: *The Defensible Normalization Proof & Best Judging Engine*

---

## 1. The Judging Integrity Problem

In distributed hackathons with dozens of judges and projects:
1. **Calibration Discrepancy**: Some judges are inherently generous (giving 4.5–5.0 to almost every project), while others are strict (rarely scoring above 3.0).
2. **Reviewer Assignment Asymmetry**: Team A might randomly be evaluated by three generous judges, receiving an unearned 4.8 average. Team B might be evaluated by three strict judges, receiving an undeserved 3.2 average despite having a superior project.
3. **Information Leakage (Lack of Role Isolation)**: In most platforms, judges can view each other's ratings before submitting their own, causing anchoring bias and collusion.

DOGFOOD resolves all three issues with:
- **Strict Backend Role Isolation**
- **Track-Affinity Load-Balanced Assignment**
- **Cross-Judge Z-Score Normalization Engine**

---

## 2. Multi-Criterion Weighted Rubric

Organizers configure dimension weights $\{w_k\}$ and maximum scores $\{M_k\}$ (defaults to $M_k = 5.0$). 
For an evaluation by judge $j$ on project $p$:

$$\text{RawScore}_{j,p} = \frac{\sum_{k=1}^m w_k \cdot s_{j,p,k}}{\sum_{k=1}^m w_k}$$

Where $s_{j,p,k}$ is the score awarded on criterion $k$.

Default Rubric Dimensions:
- **Functionality & Implementation** ($w = 1.0, M = 5.0$): Technical stability, completeness, and offline execution.
- **Innovation & Originality** ($w = 1.0, M = 5.0$): Novel approach distinct from standard templates.
- **Design Quality & Usability** ($w = 1.0, M = 5.0$): Visual ergonomics, error handling, and polish.

---

## 3. Cross-Judge Normalization Mathematics

To correct for judge bias without corrupting project merit, we standardize each judge's scoring distribution.

### Step 1: Compute Judge-Level Empirical Statistics
For each judge $j$ who evaluated $N_j$ projects:

$$\mu_j = \frac{1}{N_j} \sum_{p \in \mathcal{P}_j} \text{RawScore}_{j,p}$$

$$\sigma_j = \sqrt{\frac{1}{N_j} \sum_{p \in \mathcal{P}_j} (\text{RawScore}_{j,p} - \mu_j)^2}$$

### Step 2: Compute Global Baseline Statistics
Across all evaluations in the hackathon:

$$\mu_{\text{global}} = \frac{1}{\sum N_j} \sum_j \sum_p \text{RawScore}_{j,p}$$

$$\sigma_{\text{global}} = \sqrt{\frac{1}{\sum N_j} \sum_j \sum_p (\text{RawScore}_{j,p} - \mu_{\text{global}})^2}$$

### Step 3: Standardization (Z-Score)
For each evaluation $\text{RawScore}_{j,p}$:

$$z_{j,p} = \begin{cases} 
\frac{\text{RawScore}_{j,p} - \mu_j}{\sigma_j} & \text{if } \sigma_j > 0.001 \text{ and } N_j \ge 2 \\
\frac{\text{RawScore}_{j,p} - \mu_{\text{global}}}{\sigma_{\text{global}}} & \text{otherwise (fallback for zero variance or single review)}
\end{cases}$$

### Step 4: Rescaling to the Standard Rubric Range
We map the standardized deviation back into the global rubric scale:

$$\hat{s}_{j,p} = \text{clamp}\Big(\mu_{\text{global}} + z_{j,p} \cdot \sigma_{\text{global}}, \, 0.0, \, 5.0\Big)$$

### Step 5: Final Project Score Aggregation
The final score for project $p$, evaluated by a panel of judges $\mathcal{J}_p$, is the arithmetic mean of its normalized ratings:

$$\text{FinalScore}_p = \frac{1}{|\mathcal{J}_p|} \sum_{j \in \mathcal{J}_p} \hat{s}_{j,p}$$

---

## 4. Edge Case Handling

1. **Zero-Variance Judge ($\sigma_j = 0$)**:
   If a judge gives every project a 3.0, $\sigma_j = 0$. Dividing by zero is prevented by detecting $\sigma_j \le 0.001$. The system applies a zero Z-score ($z_{j,p} = 0.0$), ensuring their uniform rating does not artificially distort project ranks.
2. **Single-Evaluation Judge ($N_j = 1$)**:
   If a judge only reviews one project before abandoning their queue, sample standard deviation is undefined. The engine applies shrinkage toward the global population mean $(\mu_{\text{global}}, \sigma_{\text{global}})$.
3. **Bound Clamping**:
   Normalized scores are mathematically guaranteed to stay within valid rubric boundaries $[0.0, 5.0]$ using strict ceiling and floor bounds.

---

## 5. Judge Calibration Inspector

The Organizer Console provides real-time transparency into reviewer behavior via `/api/admin/calibration`:

- **Mean Score**: Average score awarded across all reviews.
- **Std Dev**: Spread of ratings.
- **Bias Rating**:
  - $\mu_j - \mu_{\text{global}} > +0.40 \implies$ **Lenient Reviewer**
  - $\mu_j - \mu_{\text{global}} < -0.40 \implies$ **Strict Reviewer**
  - $|\mu_j - \mu_{\text{global}}| \le 0.40 \implies$ **Calibrated Reviewer**

---

## 6. Role Isolation Proof

Role isolation is enforced strictly in Python on the FastAPI backend:

```python
# src/routes/judge_routes.py
if user_role == "judge":
    is_self = (current_judge_id and target_id == current_judge_id)
    if not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Role isolation prevents viewing peer judge evaluations."
        )
```

- When `judge_a` requests `/api/judge/scores`, the backend confirms identity and returns **HTTP 200**.
- When `judge_b` calls `/api/judge/scores?judge=judge_a`, the backend identifies the mismatch and returns **HTTP 403 Forbidden**.
- When `participant` calls `/api/judge/scores`, the backend confirms they are not a judge and returns **HTTP 403 Forbidden**.
- The frontend UI never possesses peer scoring data; curl requests from any external client are terminated at the API layer.

---

## 7. AI-Assisted Judging & Transparent Blending Formula

The platform integrates an automated **AI Judging Co-Pilot** that evaluates submissions on five weighted dimensions:
1. **Technical Implementation** (25%)
2. **Innovation & Novelty** (20%)
3. **Problem Relevance** (20%)
4. **Potential Impact** (20%)
5. **Usability & Polish** (15%)

### Final Score Blending Formula:
$$\text{FinalScore} = (\text{HumanScore}_{\text{norm}} \times w_{\text{human}}) + (\text{AIScore} \times w_{\text{ai}})$$

- **Default Configuration**: $w_{\text{human}} = 0.80$ (80%), $w_{\text{ai}} = 0.20$ (20%).
- **Admin Configurable**: Organizers can adjust weights via `/api/ai/weights` (e.g. 100% human / 0% AI).
- **Formula Transparency**: Every entry on the Leaderboard displays the exact formula and weight parameters applied.

### Divergence Detection & Alerting:
$$\Delta = \text{AIScore} - \text{HumanScore}_{\text{norm}}$$
If $|\Delta| \ge 1.0$, the project is flagged as **`⚠️ DIVERGENT`**, notifying organizers to inspect the qualitative reasoning, verified strengths, and missing evidence gaps before finalizing rankings. AI scores never overwrite human reviews. Full architecture and prompt structures are documented in `AI_JUDGING.md`.
