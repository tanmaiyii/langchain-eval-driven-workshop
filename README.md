# Eval-Driven Development for Agents (Offline Loop)

## From a Failing Trace to a Passing CI

![Agent Quality Evals](https://github.com/tanmaiyii/langchain-eval-driven-workshop/actions/workflows/evals.yml/badge.svg)

> *Scope: the offline reliability loop — datasets, evaluators, experiments,
> and CI gating. Online evaluation, the LangSmith Insights Agent, and the
> production flywheel are intentionally out of scope for this demo. They
> build on the same offline foundation; see "Where this sits in the bigger
> picture" below for how they fit together.*

---

## Quickstart

```bash
# 1. Clone the repo
git clone https://github.com/tanmaiyii/langchain-eval-driven-workshop.git
cd langchain-eval-driven-workshop

# 2. Install dependencies (two paths — pick one)

# Path A: uv (preferred — uses uv.lock for fully reproducible installs)
uv sync --frozen

# Path B: pip + venv (uses requirements.txt for compatibility)
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Then edit .env and fill in:
#   OPENAI_API_KEY=sk-...
#   LANGSMITH_API_KEY=lsv2_...
#   LANGSMITH_TRACING=true
#   LANGSMITH_PROJECT=agent-eval-workshop

# 4. Verify the agent traces to LangSmith
uv run python -m scripts.smoke_test

# 5. Run the regression eval suite (against support-triage-v1 dataset)
uv run python -m scripts.run_eval

# 6. Run the capability eval suite (separately, no hard-asserts)
uv run python -m scripts.run_capability_eval

# 7. Run the CI gate locally — same command GitHub Actions runs on every PR
uv run pytest tests/ -v

# 8. Open the workshop notebook
uv run jupyter lab notebook.ipynb
```

The CI gate runs automatically on every pull request to `main` via
`.github/workflows/evals.yml`. The badge at the top of this README
reflects the latest workflow status.

---

## What this demo teaches

**Eval-driven development** is the discipline of treating agent quality
as a measurable, testable property of your system rather than something
you hope works. It has four moving parts:

1. **A dataset** of input → expected-output pairs that captures what
   "correct" looks like for your agent
2. **Evaluators** that score agent runs against those expectations
3. **Experiments** that run the dataset through different agent versions
   and compare scores
4. **A CI gate** that asserts on score thresholds before code merges

Eval-driven development has **two complementary halves**:

- **Regression evals** — verify the agent still passes known cases.
  Pass rate ~100%. Hard-asserted in CI.
- **Capability evals** — track pass rate on harder examples climbing
  over time. Pass rate starts low and improves as the agent improves.
  Run in CI alongside regression but have no hard-asserts, so they
  don't block the merge.

Per LangChain's [Agent Evaluation Readiness Checklist](https://www.langchain.com/blog/agent-evaluation-readiness-checklist):
*"You need both because they serve different purposes."*

This demo uses a customer support triage agent as the **vehicle** to
demonstrate the loop. The pattern transfers to any agent with a written
policy — sales agents, ops copilots, internal assistants, anything where
"the agent should/shouldn't do X" is a rule you can encode.

---

## The demo agent

A **customer-facing customer support triage chatbot.** It handles
self-service end-to-end and submits a refund *request* for human review
when a refund is appropriate. The agent's job:

```
classify → lookup customer → search KB → resolve
```

Built with LangChain v1's `create_agent` (one constructor call) plus
`HumanInTheLoopMiddleware` for sensitive actions. Four tools:

| Tool | Purpose |
|---|---|
| `get_customer_plan` | Look up the customer's plan tier (free / pro / enterprise) |
| `search_kb` | Search the knowledge base for relevant documentation |
| `escalate` | Route the conversation to a human support agent |
| `issue_refund` | Submit a refund request for human review (NOT execute the refund) |

The system prompt is the policy document. It encodes rules like:

> *"Never refund a free-tier customer. Escalate angry customers to a
> human reviewer. Cite the relevant KB doc by ID when answering policy
> questions."*

**Why this domain.** The customer support triage agent is chosen for
its teaching properties: a real failure surface (the agent can
hallucinate refund eligibility), a hard policy rule that drives the
regression demo, and a customer-facing UX that makes the HITL semantics
coherent. The agent **submits a refund request for review** rather than
executing the refund — the customer is told the request has been
submitted and they'll receive an email; the runtime gate reviews the
request before the refund hits the processing queue. This is what
makes synchronous HITL coherent with a customer-facing chatbot: no
false claim of "refund issued" during the human-review pause.

---

## What each evaluator measures

> *These are regression evaluators — they verify the agent still passes
> known cases. Capability evaluators (which start at low pass rate and
> track improvement on harder tasks) are the complementary discipline.
> Both run via the same `client.evaluate` infrastructure and the same
> pytest CI workflow.*
>
> *Note: guardrails vs evaluators is a deliberate distinction —
> guardrails are inline runtime checks (HITL middleware blocking
> dangerous tool calls); evaluators are async scoring of agent quality.
> This demo focuses on evaluators. The HITL middleware on `issue_refund`
> is the guardrail layer — addressed via the agent's middleware config
> rather than as a separate evaluator.*

| Evaluator | Type | Measures | Calibration |
|---|---|---|---|
| `classification_correct` | Heuristic | Did the agent classify the issue correctly? | Deterministic |
| `refund_safety` | Heuristic | Did the agent avoid refunding when policy says no? | Deterministic |
| `escalation_correctness` | Heuristic | Did the agent escalate when policy says yes? | Deterministic |
| `kb_grounding` | LLM-as-judge | Is the response grounded in cited KB docs? | Requires Align Eval calibration |
| `trajectory_superset` | Heuristic | Are required tools in the call sequence? | Deterministic |
| `trajectory_judge` | LLM-as-judge | Is the trajectory reasonable for the task? | Requires Align Eval calibration |

All six follow the canonical signature
`(inputs, outputs, reference_outputs) -> {"key", "score", "comment"}`
from the [LangSmith Evaluation Quickstart](https://docs.langchain.com/langsmith/evaluation-quickstart) —
runner-agnostic, so the same evaluators work in `client.evaluate(...)`
(ad-hoc experiments) AND under pytest in CI (`tests/test_agent_quality.py`).
Notebook Cell 8 walks through one evaluator's source per type
(heuristic, LLM-judge, trajectory) so you can see how each shape maps
to the failure mode it catches.

**The CI / experiments split:**

- **CI runs both suites together** — `.github/workflows/evals.yml`
  invokes `pytest tests/` (no marker filter) on every PR. Both regression
  and capability tests execute; the gate is enforced by assertions inside
  the regression tests, not by which tests run.
- **Heuristic scores hard-assert** — deterministic, fast, free; the
  regression tests fail the PR if `refund_safety != 1`. This is the
  production gate against backsliding.
- **LLM-judge scores log to LangSmith but DON'T gate CI** — they require
  human calibration before they're trustworthy enough to gate. Until
  calibrated, gating on judges would fail PRs on judge variance, not
  real regressions.
- **Capability tests have no asserts** — they execute in the same CI
  invocation as regression but track score over time without blocking
  the merge. The `@pytest.mark.capability` marker is a local-development
  convenience for running capability in isolation
  (e.g., `pytest -m capability` for fast iteration), not a CI gate config.

---

## The 24 seed examples

**21 regression examples** in `SEED_EXAMPLES` covering:

- 8 password reset / authentication
- 6 billing inquiries (incl. `ex-005`: sounds like refund, is billing)
- 3 technical issues (incl. `ex-008`: angry → escalate)
- 3 refund requests (incl. `ex-012`: free-tier trap, `ex-019`: legitimate Pro)
- 1 multi-turn demonstration (`ex-021`: vague turn 1 → context-resolving
  turn 2). The eval target detects `inputs["messages"]: list[str]` and
  feeds turns through the same `thread_id` so the checkpointer carries
  state.

**3 capability examples** in `CAPABILITY_EXAMPLES`:

- `cap-001`: multi-issue handling
- `cap-002`: context-aware escalation
- `cap-003`: policy synthesis

Capability examples are deliberately harder. Initial pass rate is
typically 30–60%. They run in CI alongside regression on every PR
(`pytest tests/` in `.github/workflows/evals.yml`) but have no
hard-asserts, so they track score over time without blocking the merge.
`pytest -m capability` runs capability in isolation locally.

**Where evaluation earns its keep — the four traps:**

| Trap ID | Category | What's tested |
|---|---|---|
| `ex-005` | Billing-shaped refund | Easy mis-classification; the language sounds like a refund request but the resolution is billing |
| `ex-008` | Angry escalation | The agent must escalate to a human, not try to resolve in-band |
| `ex-012` | Free-tier refund | The canonical regression trap — the agent must NOT call `issue_refund`; deleting the policy line in the system prompt causes this to fail and `refund_safety` catches it |
| `ex-019` | Legitimate Pro refund | The inverse of `ex-012`; the agent SHOULD call `issue_refund` here. Tests both sides of the policy. |

**Idempotent dataset upsert.** `evals/dataset.py` keys the upsert on
`ex_id` metadata, so re-running `upsert_dataset()` updates rows in place
rather than recreating them. Same example UUIDs survive across runs —
that's what makes the LangSmith Compare view join experiments correctly
(it joins on UUID). Without stable IDs, three side-by-side experiments
would show as three disjoint datasets. Empirically verified:
`N updated, 0 created, 0 removed` on every re-run after the first.

---

## The regression demo

**The eval reliability loop in its smallest demonstrable form.**

Three named experiments captured in LangSmith:

| Experiment | What changed | Score on `refund_safety` |
|---|---|---|
| `v1-baseline` | Original prompt with the "Never refund a free-tier customer" line | 100% |
| `v2-removed-guardrail` | Deleted that one line from the system prompt | Drops on `ex-012` (the free-tier trap) |
| `v3-restored` | Line restored | Returns to 100% |

LangSmith's side-by-side comparison view shows the regression caught
visually — same dataset, three agent versions, three columns of scores.
This is the workshop's wow moment: a regression caught with the exact
failure mode visible in the trace, before any of this hits production
code.

The discipline this demonstrates:

1. Encode policy in a place that's easy to change (the system prompt)
2. Capture the canonical examples that exercise that policy (the dataset)
3. Score the agent's behavior against those examples (the evaluators)
4. Compare experiments side-by-side (LangSmith Compare view)
5. Hard-assert in CI so a regression can't merge (`pytest tests/`)

Each piece is small. The discipline is the composition.

---

## Where this sits in the bigger picture

Eval-driven development has two halves: an **offline loop** and an
**online loop**.

**This demo is the offline loop.** Curated dataset → evaluators →
experiments → CI gate. You build trust before code merges. Failures
are caught against examples you've already understood and labeled.

**The online loop is out of scope for this demo.** It's the
production-side complement: online evaluators score real user traffic,
the [LangSmith Insights Agent](https://www.langchain.com/insights-agent)
clusters production traces into recurring failure modes, those clusters
become new examples in the offline dataset, you re-run, you ship, you
repeat. Same `client.evaluate(...)` machinery on the offline side;
different infrastructure on the online side. Both halves work together —
but the offline foundation is what production tooling builds *on top of*.
A team that ships online evals without first building a regression
suite is signing up for noise without signal.

If you're standing this up from zero, do offline first. Get the
regression demo working. Then add online evals once you have a
foundation to measure against. That's the order this demo defends.

**Curriculum positioning.** This repo is the offline-loop foundation —
Module 4 of a 6-module agent-engineering sequence (Modules 1–3: agent
construction, tracing, tools/middleware; Module 5: online evals +
Insights Agent; Module 6: multi-agent). The accompanying workshop brief
lays out the full sequence; this README focuses on the working
deliverable for Module 4.

---

## Further reading

The patterns in this repo follow LangChain's canonical references —
listed here in the order to read them:

- **[LangSmith Evaluation Quickstart](https://docs.langchain.com/langsmith/evaluation-quickstart)** —
  the canonical eval pattern this repo follows: evaluator signature
  `(inputs, outputs, reference_outputs)`, dataset shape,
  `client.evaluate(...)` runner.
- **[langchain-ai/intro-to-langsmith](https://github.com/langchain-ai/intro-to-langsmith)** —
  the official LangSmith course covering tracing through evaluation.
  This repo's dependency-management pattern (`pyproject.toml` +
  `uv.lock` + `requirements.txt` all committed) mirrors it.
- **[Agent Evaluation Readiness Checklist](https://www.langchain.com/blog/agent-evaluation-readiness-checklist)** —
  the strategic context for what eval-driven development covers
  end-to-end. This repo addresses the offline portions (dataset
  construction, grader design, running/iterating, CI integration). The
  production-readiness items (online evals, user-feedback capture,
  capability→regression promotion) are the natural follow-on once the
  offline foundation is in place — out of scope for this demo.
- **[openevals](https://github.com/langchain-ai/openevals)** — pre-built
  LLM-judge templates. `create_llm_as_judge` (used by
  `evals/llm_judge_evaluators.py`) is from here.
- **[agentevals](https://github.com/langchain-ai/agentevals)** —
  trajectory-evaluation patterns. `create_trajectory_llm_as_judge` (used
  by `evals/trajectory_evaluators.py`) is from here.
- **[HumanInTheLoopMiddleware docs](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)** —
  the runtime safety layer around `issue_refund`. The eval auto-approves
  to measure agent intent; production handoff uses the four decision
  types documented here.
- **[LangSmith pytest integration](https://docs.langchain.com/langsmith/pytest)** —
  the canonical pattern for the CI gate (`@pytest.mark.langsmith`,
  `langsmith.testing` helpers, `--langsmith-output` flag). This repo's
  `tests/test_agent_quality.py` follows it directly.
