# Material Continuity

Material Continuity is a versioned, evidence-bound workflow for recovering from
critical manufacturing material disruptions. The agent coordinates the
investigation, deterministic services perform calculations and enforce
constraints, and humans retain release authority.

The current implementation includes a local web review application over the
deterministic core and fixture-backed agent workflows. It calculates production
exposure, checks approved recovery paths, compares candidate evidence, schedules
qualification, and presents recovery scenarios. Reviewers can approve a scoped
qualification task and create one mock QMS receipt. Cases, approvals, and tasks
persist in SQLite across refreshes and restarts.
Structured candidate evidence can also be compared deterministically against
application requirements with revision, applicability, unit, and provenance
checks.
Candidate qualification dependencies can be scheduled against explicit resource
calendars to distinguish supplier arrival from actual production readiness.
Recovery simulation then compares substitute qualification, original expedite,
and production resequencing without treating feasibility as authorization.
These deterministic outputs can be assembled into immutable, hash-bound
recovery-case versions with approvals and actions referencing the exact version
reviewed.

## Requirements

- Python 3.11 or newer
- No third-party packages are required for the current slice

## Run the functional web MVP

From the repository root:

```powershell
python -m services.web
```

Open **http://127.0.0.1:8000**. Demo usernames are `quality`, `engineering`, and
`planner`; the default demo password is `local-demo`. The first two roles can
approve qualification tasks. Planner can review but cannot approve these tasks.
Identity/role is resolved by the server session, not supplied by the browser.

This is a localhost-only synthetic demo, not a public production server. Override
the shared demo password with `MATERIAL_CONTINUITY_DEMO_PASSWORD` before launch
if needed. Do not use a real enterprise password for this demo. The server binds
only to `127.0.0.1`; HTTPS/SSO, public hosting and live enterprise connectors
are not implemented. Optional OpenAI review setup is described below; the
ordinary investigation workflow remains fixture-backed.

Optional launch settings:

```powershell
python -m services.web --port 8001 --database data/local/review.sqlite3
```

The default database is `data/local/review.sqlite3` (Git-ignored). To start a
separate review dataset without erasing existing records, choose another database
file, for example `--database data/local/second-review.sqlite3`.

The web application provides:

- Overview and persisted case listing.
- Case summary, approved-path search, candidate evidence, and PDF page links.
- Scenario comparison and qualification schedule, displayed in WIB.
- Server-authenticated demo login, scoped version/hash-bound approvals, and mock
  QMS tasks with persistent receipts and duplicate blocking.
- Re-investigation that preserves history and invalidates stale approvals when
  source state changes. Unchanged input does not create a new version.
- Read-only Documents & Data with the 12-PDF corpus and checksum status.
- Agent Workflow: n8n-like connected node viewer, zoom/pan, node inspector,
  accessible list mode and recorded-step replay. It is not a workflow editor.
- Explicit cost-acknowledged OpenAI review with separately persisted advisory
  history; refreshing does not issue another model request.

The canonical data retains September/October 2026 dates. Qualification dates are
planned, not completed tests. Enterprise records, evidence extraction, and QMS
actions remain synthetic/mock; document upload and actual runtime PDF extraction
are pending. Scenario costs are displayed in fixture monetary units; no currency
has been assumed.

## HTTP interface

All API calls except health/login require the session cookie. POST requests after
login also require the returned `csrf_token` in `X-CSRF-Token`.

| Route | Purpose |
|---|---|
| `GET /api/health` | Local demo status |
| `POST /api/login` | Demo username/password login |
| `GET /api/session` / `POST /api/logout` | Session identity/logout |
| `GET /api/cases` | Persisted case list |
| `GET /api/cases/{id}` | Case, current version, history, approval validation, targets, tasks, and trace |
| `GET /api/cases/{id}/evidence` | Deterministic evidence comparisons |
| `GET /api/cases/{id}/scenarios` | Simulation results |
| `POST /api/cases/{id}/investigate` | Re-run local supervisor and update immutable case versions |
| `GET /api/llm/status` | Redacted OpenAI configuration status; does not contact the provider |
| `POST /api/cases/{id}/ai-review` | Explicit optional OpenAI read-only review of a current snapshot |
| `POST /api/cases/{id}/approvals` | Approve an eligible candidate/requirement test |
| `POST /api/cases/{id}/qualification-tasks` | Execute the exact server-stored approval scope |
| `GET /api/documents` / `GET /documents/{filename}` | Corpus metadata / allowlisted PDF content |

Case mutations require the reviewed `case_version` and `case_hash`. Approvals also
require `candidate_id` and `requirement_id`; task execution requires `approval_id`.
The server derives the task name and idempotency key. Roles, actor identity, source
snapshots, and client-defined task scopes are not accepted from the request body.

SQLite read/check/write transactions serialize action creation. A unique task key
prevents duplicate writes for the same case version/candidate/requirement,
including parallel requests and multiple approvals for one target.

## Optional OpenAI review and interactive workflow

The user authorized OpenAI as an interim inference adapter while AWS access is
unavailable. AWS remains the proposal target; this is not a cloud migration or
completion of Bedrock, retrieval, PDF extraction, or the full live-agent MVP.
Open a case's **Agent Workflow** tab. The local map groups case stages, including
fixture Evidence Specialist, versioned case, human gate and mock QMS history.
Click nodes for readable backend outcomes and expandable snapshot/output JSON.
Pan/zoom the canvas, switch to an accessible list, or replay recorded steps.
The actual OpenAI trace is a separate source selection and preserves the model's
recorded tool order; it does not imply PDF extraction or a second AI agent.

**Review dengan AI** requires checking the cost/data-transfer acknowledgement
each time. While running, the UI says the current request is pending and keeps
the previous map visible; it does not animate fabricated live tool progress.
Loading, provider errors, missing configuration and stale sources are explicit.

Put your existing API key in the Git-ignored `.env.local` file **locally**, never
in chat, source code, a browser request, or a tracked file. The server reads only
the allowlisted LLM fields from this file; process environment values win. No
dotenv dependency, shell expansion or secret-writing automation is introduced.
An API key and API account quota are needed; a ChatGPT subscription is not a key.

```dotenv
MATERIAL_CONTINUITY_LLM_PROVIDER=openai
OPENAI_API_KEY=<your existing key, entered locally>
OPENAI_MODEL=<a Responses/function-calling model available to your API project>
OPENAI_TIMEOUT_SECONDS=20
OPENAI_MAX_OUTPUT_TOKENS=2048
```

There is no assumed model or silent model fallback. The default provider is
`fixtures`: finding a key alone never enables calls. Check configuration without
network traffic or credit usage with `python -m services.llm`, then restart the
web server to load changes. A `configured: true` result does **not** verify key,
model access, quota, or network connectivity.

After normal demo login, an explicit `POST /api/cases/CASE-001/ai-review` with the
same CSRF header and reviewed `case_version`/`case_hash` as other case requests
runs the review. It can incur API charges and sends the selected synthetic case
facts/provenance to OpenAI. No call happens during startup, login, case browsing,
or ordinary re-investigation. `store: false` disables Responses storage; it is
not a claim about all provider data-retention policies.

The model chooses read-only tools for existing backend-calculated exposure,
approved-path discovery, candidate evidence, qualification schedules and recovery
scenarios, then returns a structured Indonesian advisory. Code enforces the
approved-first prerequisites and checks all candidates before allowing a final
review. It cannot call approval, purchasing, release or task-creation tools.
Numerical/status/citation facts are returned separately, copied unchanged from
the case; generated prose is advisory, not verified evidence or authorization.

Limits: one concurrent review per server, at most 12 model calls per review,
90 seconds total, 20 seconds per HTTP call by default, bounded context/output,
and no automatic retry. Provider errors are sanitized. Cases and source hashes
are checked before and after inference; changed inputs discard the result.
Successful review results are persisted in the separate SQLite `ai_reviews`
table, never added to decision hashes or treated as technical evidence. The
latest review is restored by the case API and survives refresh/restart without
another API charge. Old case hashes or changed sources mark it as an archive;
its graph uses its original reviewed snapshot, never silently mixes new facts.
Existing cases, approvals, actions and QMS receipts remain unchanged. Review
failures or source changes during inference do not save an apparently successful
review. Failed runs are not yet persisted as per-node execution traces.

Contract references: [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling)
and [Responses API](https://developers.openai.com/api/reference/responses/overview).
All automated integration tests use fake responses. A separate manual live smoke
test on 2026-10-22 succeeded with the user's existing key and `gpt-5.4-mini`:
8 calls reviewed synthetic CASE-001 Version 1 without changing the case or its
authorization state. Reported usage was 30,109 input and 579 output tokens.
That first test used an in-memory provider override. The user then approved web
activation: the local provider is now `openai` and a browser-initiated review was
verified with 8 calls (30,372 input / 491 output tokens). The same result survived
reload without another model call. These are smoke tests, not claims about
ongoing quota, model reliability or deployed factory benefit. The example config
still defaults to `fixtures` for new installations. Next: implement controlled
document ingestion/extraction and ingestion-driven re-investigation.

Offline frontend tests (Node.js, no packages):

```powershell
node --test tests/web/workflow.test.cjs
```

## Run the canonical exposure scenario

```powershell
python -m core.exposure --material MAT-BRG-001 --as-of 2026-09-29T00:00:00+00:00
```

## Run recovery-option discovery

```powershell
python -m core.recovery_options --material MAT-BRG-001 --required-quantity 700 --need-by 2026-10-04 --as-of 2026-09-29
```

## Compare candidate evidence

```powershell
python -m core.requirements --candidate CAND-A
python -m core.requirements --candidate CAND-B
```

## Build the qualification graph

```powershell
python -m core.qualification --candidate CAND-A
```

## Compare recovery scenarios

```powershell
python -m core.simulation --material MAT-BRG-001 --as-of 2026-09-29T00:00:00+00:00 --shortage-at 2026-10-04T00:00:00+00:00
```

## Build the canonical recovery case

```powershell
python -m core.case_state --case-id CASE-001
```

## Run tests

```powershell
python -m unittest discover -s tests -v
```

For architecture, business logic, current progress, and AI-agent handoff
context, see [PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md).
