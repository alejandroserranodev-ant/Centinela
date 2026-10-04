# The challenge Centinela answers

This page is the requirement every other level builds against. It digests
[`hackathon-brief.pdf`](./hackathon-brief.pdf), the deck of the Business AI School hackathon by
On Business, and it is the only page that restates it. A level that needs a requirement links here
instead of copying it.

## What is asked

Centinela is a system of AI agents that **watches the business data** of `Distribuidora Andina
S.A.S.`, detects a problem before it costs money, explains why it happens, and proposes the action
that corrects it, executing it only after a person approves. It replaces a dashboard someone has to
look at with an operation that watches itself. The deliverables are a working MVP, a five-minute
demo and a three-minute business pitch, built in three days by a team covering business, data,
backend and frontend.

The dataset carries five announced business problems and one hidden one revealed at the close:
an eroding margin, growing overdue debt (`mora`), an imminent stock-out, discounts outside policy,
and a customer who is leaving. Which entities they affect is not given; Centinela discovers it.
The jury uses those seeded scenarios to test every solution.

## MVP scope

**Required (base):**

- `Vigía` detects at least three of the five announced scenarios.
- `Analista` explains the cause with evidence.
- A decision inbox (`bandeja`) with approve and reject.
- A chat to ask questions about the data.
- A log (`bitácora`) of every decision.

**Out of scope**, and presented in the pitch as roadmap: connection to real customer systems,
full enterprise authentication, and production deployment.

## The agents

Three agents read, one acts, and it acts only after approval.

| Agent | Does | Example output |
|---|---|---|
| `Vigía` | reviews the KPIs and detects anomalies or trends against rules and statistics | "the margin of line Hogar fell 6 points in 3 weeks" |
| `Analista` | finds the root cause by crossing data and consulting the policies | "supplier X raised the cost of 4 SKUs" |
| `Estratega` | proposes one to three actions with impact in pesos and a confidence level | "raise price 3% on 4 SKUs recovers $42 M/month" |
| `Ejecutor` | executes the approved action with permitted tools and leaves a record | a draft email, a task, a draft purchase order |

The **orchestrator** coordinates the agents, keeps the state of each alert, and stops the flow
before any action with an external effect.

## The user's journey

1. Opens the inbox: decisions ordered by pesos at risk.
2. Opens an alert: what happened, why (with evidence), what is proposed and what it is worth.
3. Asks in natural language, for example "which other customers buy those SKUs?".
4. Decides: approve, edit or reject. A rejection asks for the reason, and Centinela learns from it.
5. The `Ejecutor` acts and everything lands in the audit log.

**Principle: the user does not look for the problem; the problem reaches the user, explained and
with a proposal ready to approve.**

## Reference architecture and stack

The brief recommends a stack and lets a team change a piece it can justify:

| Layer | The brief recommends | Alternatives the brief accepts |
|---|---|---|
| language models | Claude: a large model to reason, a fast one to classify | GPT, Gemini; open models through Ollama |
| orchestration | LangGraph, for state and the pause for human approval | Claude Agent SDK, OpenAI Agents SDK, ADK, CrewAI |
| tools | MCP servers: read-only SQL, policies, actions | the model's native function calling |
| data | PostgreSQL + pgvector | DuckDB for local analysis |
| anomaly detection | business rules + statistics (z-score, trend) | scikit-learn Isolation Forest, Prophet |
| backend | Python + FastAPI + Pydantic | Node.js + Hono or NestJS |
| frontend | Next.js + React + Tailwind + shadcn/ui + Recharts | Streamlit for a prototype only, which lowers the UX score |
| observability and evals | Langfuse + promptfoo | LangSmith, Arize Phoenix, Ragas |
| deployment | Docker Compose; demo on Cloud Run, Render or Vercel | local with a secure tunnel |

Each level states the piece it chose and why, on its own page. How the whole system is deployed
for the demo is chosen on no level.

**Golden rule: SQL or Python computes every number; the model reasons, explains and writes, and
never invents a figure.**

## Backend properties the brief requires

- **Semantic layer:** KPIs defined once as SQL views; agents never query raw tables.
- **Simulated clock:** an endpoint advances the operation day by day, so the jury watches alerts appear.
- **Lifecycle:** `nueva` → `en análisis` → `propuesta` → `aprobada` or `rechazada` → `ejecutada`, persisted.
- **Human approval:** the flow stops before any external action; without approval there is no action.
- **Safe actions:** a closed list of tools, idempotent, in draft or sandbox.
- **Prioritisation:** alerts ordered by pesos at risk; one cause does not raise ten alerts.
- **Cost and latency:** the fast model for simple steps, caching, a token cap, cost recorded per alert.
- **Robustness:** retries, timeouts, and "I do not have enough evidence" as a valid answer.

## Minimal API

| Method | Path | Purpose |
|---|---|---|
| POST | `/simulacion/avanzar?dias=1` | moves the clock and triggers `Vigía` |
| GET | `/alertas?estado=propuesta` | the decision inbox |
| GET | `/alertas/{id}` | cause, evidence and actions |
| POST | `/alertas/{id}/decision` | approve, edit or reject, with a reason |
| POST | `/chat` | natural-language questions, streamed |
| GET | `/bitacora` | audit of decisions and actions |

## Screens

| Screen | For whom | Shows |
|---|---|---|
| `Bandeja de decisiones` | manager, process leads | alerts by pesos at risk, with urgency, confidence and actions |
| `Detalle de alerta` | process leads | what happened, cause with evidence, proposed actions with impact, approval |
| `Chat anclado` | everyone | questions on the alert or the data; answers with figure, chart and source |
| `Bitácora` | audit, management | who approved what and when, what the agent executed and with what result |
| `Configuración` | analyst | watched KPIs, thresholds, owners, and autonomy level per action type |

UX criteria: value in 30 seconds (money at risk today and the three key decisions); explanation in
three levels (one sentence, then evidence, then "how I got here" with the queries); the human
decides in one click and a rejection asks for a reason; assumptions and confidence are visible and
doubt is said; the agent's current step is visible while it works; business language, Colombian
pesos, clear dates, no jargon; accessible and responsive (severity not by colour alone, keyboard,
phone).

## Responsible AI

| Risk | Minimum control |
|---|---|
| invented figures | every number comes from a logged query, and the answer links the query that produced it |
| unwanted action | human approval before any external action; closed tool list; draft mode |
| prompt injection | data and documents are data, never orders; the jury plants a malicious text in a policy |
| improper data access | a read-only database user; roles per area |
| personal data | mask sensitive data before sending it to a model (Colombian Ley 1581) |
| missing traceability | an immutable log: alert, evidence, proposal, decision, action, result |
| agent degradation | an evaluation set built on the seeded scenarios, run on every significant change |

Autonomy has three levels per action type: `Informa`, `Propone`, `Ejecuta`. **During the hackathon
everything stays at `Propone`**; full autonomy is earned in production with a track record.
