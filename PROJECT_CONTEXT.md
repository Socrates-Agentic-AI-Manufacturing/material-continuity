# Material Continuity — Project Context, Architecture, and Progress Tracker

> **Purpose of this file**
>
> This document is the primary handoff/context file for any local AI coding agent (Codex, Claude Code, Copilot, etc.) working on the **Material Continuity** project.
>
> Read this file **before making architectural changes, generating code, adding dependencies, or changing business logic**.
>
> The project originated from the final-stage proposal for an Agentic AI hackathon under the **Intelligence Manufacturing** track.
>
> This file contains:
> - the project problem and scope;
> - proposal-derived requirements;
> - implementation decisions and recommendations;
> - architecture and component responsibilities;
> - deterministic vs agentic boundaries;
> - data model and tool contracts;
> - UI and demo flow;
> - security / approval boundaries;
> - repo structure;
> - milestone checklist;
> - progress tracker;
> - architecture decision log;
> - test / acceptance criteria;
> - open questions and risks;
> - instructions for future AI agents.
>
> **Important:** Sections marked `[PROPOSAL]` are grounded in the submitted proposal.
> Sections marked `[IMPLEMENTATION]` are implementation recommendations derived from the proposal and may be changed deliberately if there is a better reason.
> Sections marked `[CURRENT DECISION]` represent decisions already made in this project conversation and should not be changed casually.

---

# 0. Project Identity

## Project name

**Material Continuity**

## Repository strategy

`[CURRENT DECISION]`

Use **one GitHub organization + one monorepo** for the hackathon MVP.

Suggested organization name:

```text
material-continuity
```

Suggested repository name:

```text
material-continuity
```

Reason:
- team size is 3;
- MVP scope is tightly coupled;
- frontend, agent orchestration, deterministic tools, mock enterprise data, and AWS infrastructure need frequent integration;
- multi-repo would add unnecessary coordination and CI/CD overhead for the hackathon stage.

---

# 1. Executive Summary

`[PROPOSAL]`

Material Continuity handles a manufacturing recovery problem that appears when a **critical purchased component becomes unavailable, delayed, or quarantined** and no immediately usable approved option can meet the required production date.

The key business insight is:

> **Availability does not imply usability.**

A replacement component can be physically available but still unusable because:
- engineering requirements are not fully satisfied;
- application-specific evidence is missing;
- the available evidence belongs to the wrong revision;
- a required qualification test is incomplete;
- a deviation has expired;
- Quality has not released the component;
- qualification may complete only after the production shortage occurs.

The system therefore does not merely answer:

> “Can we obtain another component?”

It must answer:

> **“Can an alternative become qualified and usable before the remaining recovery window closes, and what evidence and approvals are still required?”**

The project focuses on a pilot scenario involving **purchased bearings used directly in assembly BOMs**, not maintenance spares.

---

# 2. Precise Problem Statement

`[PROPOSAL]`

When a critical component is delayed or quarantined:

1. Planning must determine which production orders are exposed.
2. Procurement checks available supply, supplier ETA, and quotes.
3. Engineering checks application requirements, drawings, limits, and revisions.
4. Quality checks qualification status, tests, supplier approval, and deviations.
5. Production evaluates whether resequencing can protect output.

A purchase decision made before those answers agree can convert a **material shortage** into a **quality incident**.

The pilot therefore aims to:

> **Compress the time required to establish an approvable, time-feasible recovery plan when immediately usable approved options are exhausted, while preserving Engineering and Quality release authority.**

---

# 3. Core Product Thesis

`[PROPOSAL]`

Material Continuity is **not**:
- a generic RAG chatbot;
- a procurement agent;
- a supplier search engine;
- a predictive maintenance product;
- a generic manufacturing assistant;
- a free-form LLM recommendation system;
- an autonomous release system.

It is a:

> **Versioned, evidence-bound recovery decision workflow for material disruption.**

The central output is a **recovery case** linking:

```text
production exposure
→ recovery options
→ technical requirements
→ evidence per requirement
→ unresolved gaps
→ qualification dependencies
→ recovery timing
→ human approvals
→ authorized action
```

---

# 4. Non-Negotiable Design Principles

These principles should remain stable unless the team explicitly changes the proposal strategy.

## 4.1 Arrival is not readiness

`[PROPOSAL]`

A candidate arriving before depletion is not necessarily usable before depletion.

Example:

```text
Usable stock:            300 bearings
Demand:                  100/day
Stock depletion:         after Day 3
Candidate ETA:           Day 2
Qualification complete:  Day 5
```

Therefore:

```text
arrives before shortage = YES
usable before shortage  = NO
```

---

## 4.2 Missing evidence must remain visible

`[PROPOSAL]`

If an application-specific requirement is not supported by evidence:

```text
Status = UNKNOWN
```

Do **not** silently infer compatibility.

Allowed requirement states:

```text
MATCH
MISMATCH
UNKNOWN
BLOCKED
```

Suggested semantics:

- `MATCH`: sufficient applicable evidence supports the requirement.
- `MISMATCH`: evidence explicitly violates the requirement.
- `UNKNOWN`: required evidence is missing, insufficient, conflicting, or not applicable enough.
- `BLOCKED`: release/qualification state prevents use even if technical attributes appear compatible.

---

## 4.3 Hard mismatches reject

`[PROPOSAL]`

If a hard requirement is violated, the candidate must not progress as a valid replacement.

Example:

```text
Required bore = 25 mm
Candidate bore = 30 mm
Result = MISMATCH
Decision = REJECT
```

---

## 4.4 Unknown is not match

`[PROPOSAL]`

A missing document, missing test, expired deviation, or unresolved conflicting evidence must not be converted into a confident positive conclusion.

---

## 4.5 LLM interprets and orchestrates; code calculates and enforces; humans authorize

`[CURRENT DECISION]`

This sentence is the implementation boundary for the entire MVP:

> **LLM interprets and orchestrates. Code calculates and enforces. Human authorizes.**

### LLM / agent responsibilities

- tool selection;
- understanding the recovery objective;
- interpreting heterogeneous documents;
- extracting structured evidence;
- evidence synthesis;
- identifying missing evidence;
- determining which investigation/tool to perform next;
- explaining recovery scenarios.

### Deterministic code responsibilities

- stock arithmetic;
- time-phased shortage calculation;
- dimensional/unit comparisons;
- hard constraints;
- qualification timing;
- dependency graph calculations;
- scenario cost/timing calculations;
- action authorization checks;
- case-version validation;
- idempotency enforcement.

### Human responsibilities

- Engineering review;
- Quality review;
- approving qualification tasks;
- approving controlled actions where required;
- final material release authority.

---

# 5. MVP Scope

`[PROPOSAL]`

The submitted MVP scope is intentionally narrow.

## Data scope

- one bearing family;
- three candidate records;
- two assembly BOMs;
- ten production orders;
- twelve text-based technical/quality documents;
- stock fixtures;
- supplier fixtures;
- test-calendar fixtures;
- one plant;
- transfer lookup;
- synthetic enterprise data;
- mock test results.

## Technical scope

- Recovery Supervisor;
- Evidence Specialist;
- Amazon Bedrock inference;
- AgentCore Runtime;
- AgentCore Gateway;
- Amazon S3;
- Bedrock Managed Knowledge Base;
- EventBridge;
- Lambda;
- controlled tools;
- review UI;
- versioned recovery case;
- approval gate;
- mock enterprise action receipt.

## Explicitly post-MVP / not required

`[PROPOSAL]`

- live SAP write-back;
- unrestricted procurement;
- real supplier onboarding;
- complex technical drawing interpretation;
- physical qualification execution;
- deployed factory benefit;
- automatic BOM release.

---

# 6. Canonical Demo Scenario

`[PROPOSAL]`

The final demo should be built around **one coherent end-to-end failure-and-recovery story**, not a collection of unrelated features.

## Demo sequence

1. Inject a delayed delivery.
2. Identify the affected/exposed production orders.
3. Confirm no timely approved source can meet the need date.
4. Discover unqualified candidate alternatives.
5. Reject one candidate due to a hard mismatch.
6. Flag another candidate because application-specific temperature/lubricant evidence is missing.
7. Compare three recovery paths.
8. A human reviewer approves a qualification task.
9. The action adapter creates a mock QMS task/identifier.
10. Production release remains blocked.
11. Update the source document revision.
12. Re-open the case.
13. Invalidate the previous authorization because it belongs to an older case/evidence version.

## This scenario is the primary definition of done.

If a feature does not materially improve this story, it is lower priority during the hackathon.

---

# 7. Recovery Workflow

`[PROPOSAL]`

The recovery process has five major stages.

## 7.1 Sense / Assess

Input:

```text
ERP/QMS disruption event
```

Examples:
- delivery delay;
- quality hold;
- stock exception;
- component quarantine.

Actions:
- deduplicate event;
- retrieve current stock;
- retrieve holds;
- retrieve confirmed receipts;
- retrieve dated demand / production orders;
- compute time-phased shortage.

Important:

> The shortage date must be calculated by deterministic code, not estimated by the LLM.

---

## 7.2 Discover

Search in the following order:

```text
1. network stock
2. approved source
3. approved equivalent
4. alternate BOM
5. still-valid deviation
6. unqualified candidates
7. original-part expedite
8. production resequencing
```

Do not jump directly to unqualified substitutes if an already-approved recovery path is sufficient.

---

## 7.3 Verify

For each candidate:

- retrieve revision-specific evidence;
- retrieve application requirements;
- normalize units;
- compare evidence to explicit limits;
- record source / revision / page / applicability;
- classify each requirement;
- identify missing/conflicting evidence;
- identify required qualification tests.

Rules:

```text
hard MISMATCH → reject candidate
critical UNKNOWN → block release / require evidence or test
missing evidence → never auto-MATCH
```

---

## 7.4 Simulate

Build a qualification dependency graph.

Example:

```text
supplier confirmation
        ↓
candidate delivery
        ↓
temperature test
        ↓
engineering review
        ↓
quality review
        ↓
qualification release
```

Use:
- test durations;
- resource calendars;
- delivery dates;
- approval dependencies;
- current production shortage date.

Compare at least:

```text
A. substitute + qualification
B. original-part expedite
C. production resequencing
```

Rank or present feasible recovery scenarios using deterministic outputs such as:
- exposed orders;
- recovery date;
- incremental cost;
- qualification completion date;
- feasibility;
- unresolved conditions.

Unknown completion times must remain unresolved.

---

## 7.5 Approve / Act / Learn

Agent-generated recommendations are not authorization.

Before executing an action:

- verify approver identity;
- verify approver role;
- verify allowed action;
- verify case version;
- verify case hash;
- verify approval expiry;
- re-read changing stock/evidence where relevant;
- enforce idempotency;
- log an action receipt.

A qualification task approval does **not** release the material for production.

---

# 8. High-Level Architecture

`[PROPOSAL + IMPLEMENTATION]`

```text
                    ┌───────────────────────┐
                    │  Disruption Event     │
                    │ ERP / QMS / Fixture   │
                    └───────────┬───────────┘
                                │
                           EventBridge
                                │
                                ▼
                    ┌───────────────────────┐
                    │ Recovery Supervisor   │
                    │ Agent / Orchestrator  │
                    └───────────┬───────────┘
                                │
       ┌────────────────────────┼─────────────────────────┐
       │                        │                         │
       ▼                        ▼                         ▼
┌───────────────┐       ┌────────────────┐       ┌─────────────────┐
│ Exposure Tool │       │ Recovery       │       │ Evidence        │
│ Deterministic │       │ Options Tool   │       │ Specialist      │
└───────────────┘       └────────────────┘       └────────┬────────┘
                                                        │
                                                        ▼
                                            S3 + Bedrock Knowledge Base
                                                        │
       ┌────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────┐
│ Versioned Recovery Case │
│ Evidence + gaps + state │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Qualification Graph     │
│ Deterministic timing    │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Recovery Simulation     │
│ Deterministic scenarios │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Human Approval Gate     │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Action Adapter          │
│ role/version/idempotency│
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Mock ERP / QMS Action   │
│ + Action Receipt        │
└─────────────────────────┘
```

---

# 9. Agent Architecture

## 9.1 Recovery Supervisor

`[PROPOSAL]`

Primary role:
- orchestrate the recovery case;
- choose the next tool;
- branch based on results;
- maintain case context;
- coordinate evidence investigation;
- request simulations;
- present recovery scenarios.

The supervisor should **not** perform deterministic business calculations itself.

Expected tools:

```text
getExposure()
findRecoveryOptions()
compareRequirements()
simulateRecovery()
createQualificationTask()
```

Possible additional implementation tools:

```text
getCase()
updateCase()
getCandidateEvidence()
getQualificationDependencies()
validateApproval()
executeAuthorizedAction()
```

---

## 9.2 Evidence Specialist

`[PROPOSAL]`

Responsibilities:
- retrieve technical/quality evidence;
- identify correct document revision;
- extract candidate specifications;
- map evidence to specific application requirements;
- normalize units;
- identify evidence gaps;
- identify qualification dependencies;
- preserve provenance.

Expected output should be structured.

Example:

```json
{
  "candidate_id": "CAND-A",
  "requirement_id": "REQ-LOAD-001",
  "requirement": "Dynamic load",
  "required_operator": ">=",
  "required_value": 14,
  "required_unit": "kN",
  "observed_value": 16,
  "observed_unit": "kN",
  "status": "MATCH",
  "evidence": {
    "document": "Candidate_A_Datasheet_Rev2.pdf",
    "revision": "2",
    "page": 3,
    "location": "Dynamic load rating table"
  }
}
```

---

# 10. Deterministic Core

`[IMPLEMENTATION]`

Build this before depending heavily on agents.

The MVP should function with mocked/structured inputs before document retrieval and agent orchestration are added.

## 10.1 `getExposure()`

Purpose:
- determine when usable stock is depleted;
- identify exposed production orders.

Inputs:

```json
{
  "material_id": "BRG-001",
  "as_of": "ISO-8601 timestamp"
}
```

Expected calculations:

```text
available stock
+ confirmed receipts by date
- allocations
- time-phased BOM consumption
= projected availability
```

Outputs:

```json
{
  "material_id": "BRG-001",
  "current_usable_stock": 300,
  "shortage_date": "2026-10-04",
  "affected_orders": [
    {
      "order_id": "PO-006",
      "due_date": "2026-10-04",
      "unserved_qty": 100
    }
  ]
}
```

---

## 10.2 `findRecoveryOptions()`

Purpose:
search for recovery paths in the required order.

Possible output:

```json
{
  "approved_options": [],
  "unqualified_candidates": [
    "CAND-A",
    "CAND-B"
  ],
  "fallbacks": [
    "EXPEDITE_ORIGINAL",
    "RESEQUENCE_PRODUCTION"
  ]
}
```

---

## 10.3 `compareRequirements()`

Purpose:
perform deterministic comparison after evidence extraction.

Input:

```json
{
  "requirement": {
    "name": "Bore",
    "operator": "=",
    "value": 25,
    "unit": "mm",
    "critical": true
  },
  "candidate_evidence": {
    "value": 25,
    "unit": "mm",
    "source": "Candidate_A_Datasheet_Rev2.pdf",
    "revision": "2",
    "page": 2
  }
}
```

Output:

```json
{
  "status": "MATCH",
  "normalized_required_value": 25,
  "normalized_observed_value": 25,
  "unit": "mm"
}
```

Hard rule:
- comparison result must be reproducible;
- LLM text must not determine numerical compatibility.

---

## 10.4 `simulateRecovery()`

Purpose:
compute when a recovery option becomes usable and compare it with the shortage window.

Input example:

```json
{
  "candidate_id": "CAND-A",
  "arrival_date": "2026-10-03",
  "shortage_date": "2026-10-04",
  "dependencies": [
    {
      "task": "temperature_test",
      "duration_hours": 16
    },
    {
      "task": "engineering_review",
      "duration_hours": 4
    },
    {
      "task": "quality_release",
      "duration_hours": 4
    }
  ]
}
```

Output:

```json
{
  "arrival_date": "2026-10-03",
  "qualification_complete": "2026-10-05",
  "shortage_date": "2026-10-04",
  "feasible_before_shortage": false,
  "delay_after_shortage_hours": 24
}
```

---

# 11. Recovery Case Model

`[PROPOSAL + IMPLEMENTATION]`

The recovery case is a first-class object.

Suggested structure:

```json
{
  "case_id": "CASE-001",
  "case_version": 3,
  "status": "UNDER_REVIEW",
  "trigger": {
    "type": "DELIVERY_DELAY",
    "material_id": "BRG-001"
  },
  "exposure": {},
  "recovery_options": [],
  "candidates": [],
  "evidence_matrix": [],
  "qualification_dependencies": [],
  "scenarios": [],
  "approvals": [],
  "actions": [],
  "source_versions": [],
  "created_at": "",
  "updated_at": ""
}
```

## Case-version rules

A case version should change when information that can materially change the decision changes, for example:

- source document revision changes;
- supplier ETA changes;
- stock quantity changes significantly;
- test result changes;
- qualification requirement changes;
- production order timing changes;
- candidate evidence changes.

An approval is valid only for the case/evidence version it reviewed.

---

# 12. Evidence Model

`[PROPOSAL]`

Every supported requirement row should retain:

```text
requirement
candidate value
normalized value
source document
document revision
page/location
applicability
status
```

Example matrix:

| Requirement | Candidate | Evidence | Status |
|---|---:|---|---|
| Bore = 25 mm | 25 mm | Datasheet Rev2 p.2 | MATCH |
| Dynamic load ≥ 14 kN | 16 kN | Datasheet Rev2 p.3 | MATCH |
| Lubricant suitability at operating temperature | Not evidenced | No application-specific evidence | UNKNOWN |
| Plant qualification release | Not released | QMS fixture | BLOCKED |

---

# 13. Synthetic Data Model

`[IMPLEMENTATION]`

The following tables/entities are recommended for the MVP.

## 13.1 Materials

```text
material_id
description
material_family
approved_status
current_stock
unit
```

## 13.2 BOM

```text
product_id
material_id
quantity_required
bom_revision
valid_from
valid_to
```

## 13.3 Production Orders

```text
order_id
product_id
quantity
scheduled_date
due_date
priority
status
```

## 13.4 Purchase Orders / Receipts

```text
po_id
material_id
supplier_id
quantity
expected_delivery
status
```

## 13.5 Suppliers / Candidate Availability

```text
supplier_id
candidate_id
available_qty
eta
quoted_price
quote_timestamp
```

## 13.6 Engineering Requirements

```text
requirement_id
product_id
application_id
property
operator
required_value
unit
criticality
source_document
source_revision
```

## 13.7 Candidate Specifications

```text
candidate_id
property
value
unit
source_document
source_revision
source_page
```

## 13.8 Qualification Tests

```text
test_id
candidate_id
requirement_id
procedure_id
duration_hours
required_resource
status
result
```

## 13.9 Deviations

```text
deviation_id
candidate_id
scope
valid_from
valid_until
approval_status
```

## 13.10 Approvals

```text
approval_id
case_id
case_version
case_hash
approver_id
approver_role
permitted_action
approved_at
expires_at
```

## 13.11 Action Receipts

```text
action_id
case_id
case_version
action_type
external_reference
idempotency_key
status
executed_at
```

---

# 14. Document / Retrieval Layer

`[PROPOSAL + IMPLEMENTATION]`

Target architecture:

```text
Engineering / Quality Documents
            ↓
           S3
            ↓
Bedrock Managed Knowledge Base
            ↓
Evidence Specialist
            ↓
Structured evidence
            ↓
Deterministic requirement comparison
```

Recommended synthetic document set:

```text
Candidate_A_Datasheet_Rev2.pdf
Candidate_A_Certificate.pdf
Candidate_B_Datasheet.pdf
Candidate_C_Datasheet.pdf

Engineering_Drawing_Assembly_A.pdf
Engineering_Drawing_Assembly_B.pdf
Bearing_Application_Requirements.pdf

Qualification_SOP_Temperature.pdf
Qualification_SOP_Load.pdf

Approved_Supplier_List.pdf
Existing_Deviation.pdf
Quality_Release_Procedure.pdf
```

The exact filenames may change.

The retrieval layer must preserve:
- document identity;
- revision;
- page/location;
- applicability;
- extraction confidence if implemented;
- source version.

---

# 15. Qualification Dependency Graph

`[PROPOSAL + IMPLEMENTATION]`

Candidate readiness must follow the critical path of remaining work.

Example:

```text
Candidate selected
      │
      ▼
Supplier delivery
      │
      ▼
Temperature test
      │
      ▼
Engineering review
      │
      ▼
Quality review
      │
      ▼
Qualification release
      │
      ▼
Usable for production
```

Do not equate:
- supplier ETA;
- test completion;
- approval;
- production release.

These are distinct lifecycle states.

---

# 16. Recovery Scenarios

`[PROPOSAL]`

At minimum compare:

## Scenario A — Substitute + Qualification

Variables:
- candidate ETA;
- missing evidence;
- qualification test duration;
- Engineering review;
- Quality review;
- incremental cost;
- qualification completion date.

## Scenario B — Original-Part Expedite

Variables:
- expedited ETA;
- expedite cost;
- quantity;
- production coverage.

## Scenario C — Production Resequencing

Variables:
- alternative order sequence;
- available material;
- protected orders;
- deferred orders;
- changeover / operational impact if modeled.

Output example:

| Recovery Option | Ready Date | Exposed Orders | Incremental Cost | Decision State |
|---|---|---:|---:|---|
| Candidate A + Qualification | Day 5 | 2 | 3,000 | CONDITIONAL |
| Original Expedite | Day 4 | 1 | 7,500 | FEASIBLE |
| Production Resequencing | Day 3 | 0 initially | 2,000 | TEMPORARY BRIDGE |

The numbers above are illustrative only.

---

# 17. Human Approval and Action Gate

`[PROPOSAL]`

The agent must not possess:
- unrestricted purchasing authority;
- BOM release authority;
- automatic production release authority.

Before an action executes, validate:

```text
authenticated user
approver role
permitted action
case ID
case version
case hash
approval expiry
source freshness
idempotency key
```

### Failure behavior

Fail closed if:
- approval is stale;
- source revision changed;
- case version changed;
- role is unauthorized;
- approval expired;
- action is outside permitted scope;
- duplicate action already executed.

---

# 18. Stale Approval Demo

`[CURRENT DECISION]`

This should be intentionally demonstrated because it clearly differentiates the project.

Example:

```text
Case Version 3
Candidate A
Datasheet Revision 2

Quality approves:
CREATE_QUALIFICATION_TASK
```

Then replace:

```text
Candidate_A_Datasheet_Rev2.pdf
```

with:

```text
Candidate_A_Datasheet_Rev3.pdf
```

System behavior:

```text
new evidence version detected
case version: 3 → 4
previous authorization: INVALID
```

If execution is attempted:

```text
ACTION BLOCKED

Authorization belongs to Case Version 3.
Current Case Version is 4.
Re-review required.
```

---

# 19. Action Adapter

`[PROPOSAL + IMPLEMENTATION]`

The MVP does not require a live SAP write-back.

The action adapter may mock an enterprise QMS/ERP write.

Primary MVP action:

```text
createQualificationTask()
```

Example result:

```json
{
  "status": "CREATED",
  "qms_task_id": "QMS-QUAL-00421",
  "case_id": "CASE-001",
  "case_version": 3,
  "timestamp": "2026-10-XXTXX:XX:XXZ",
  "idempotency_key": "..."
}
```

Important:

```text
Qualification task created ≠ material released
```

Production release must remain blocked until the appropriate lifecycle criteria are satisfied.

---

# 20. AWS Service Mapping

`[PROPOSAL]`

Target services:

## Amazon Bedrock

Use for:
- document interpretation;
- adaptive reasoning;
- evidence synthesis;
- tool selection.

## Amazon Bedrock AgentCore Runtime

Use for:
- hosting agent runtime;
- Recovery Supervisor;
- Evidence Specialist.

## AgentCore Gateway

Use for:
- controlled tool exposure;
- API/Lambda targets;
- constrained agent access.

## Amazon S3

Use for:
- technical documents;
- quality documents;
- source versions;
- potentially audit artifacts.

## Bedrock Managed Knowledge Base

Use for:
- document parsing;
- retrieval;
- evidence grounding.

## AWS Lambda

Use for:
- deterministic arithmetic;
- requirement checks;
- exposure calculation;
- recovery simulation;
- approval-policy enforcement;
- action adapter.

## EventBridge

Use for:
- disruption event trigger;
- event-driven invocation.

## CloudWatch / AgentCore Observability

Use for:
- tool-call traces;
- logs;
- errors;
- agent execution visibility;
- audit support.

## IAM

Use least privilege.

Do not rely on retrieved documents as authorization.

---

# 21. AWS Validation Checklist

`[IMPLEMENTATION]`

Perform early before committing architecture details:

- [ ] Confirm AWS account access from hackathon.
- [ ] Confirm target AWS Region.
- [ ] Confirm Bedrock model availability.
- [ ] Confirm AgentCore Runtime availability.
- [ ] Confirm AgentCore Gateway availability.
- [ ] Confirm Knowledge Base availability.
- [ ] Confirm S3 permissions.
- [ ] Confirm Lambda deployment access.
- [ ] Confirm EventBridge access.
- [ ] Confirm CloudWatch access.
- [ ] Identify quota limitations.
- [ ] Identify allowed model(s).
- [ ] Record all required environment variables.

Validation attempt on 2026-09-29 is currently blocked: the local environment has
no AWS CLI, AWS SDK, configured AWS Region/profile/credentials, Bedrock model or
Knowledge Base ID, or S3 document bucket. No AWS checklist item is considered
complete until hackathon account access is supplied and verified read-only.

If AgentCore access is unavailable, preserve the logical architecture and use a compatible fallback runtime rather than rewriting the product concept.

---

# 22. UI / UX Scope

`[IMPLEMENTATION]`

Keep the frontend compact.

## 2026-10-13 planning update

The user has chosen to proceed directly to the web UI rather than prioritizing a
separate standalone end-to-end CLI demo runner. Demonstrate the canonical
acceptance flow through the web application while reusing the existing core.

The latest proposed web structure has six functional areas:

1. Overview / Cases;
2. Recovery Case details and recovery discovery;
3. Evidence Review;
4. Recovery Scenarios / qualification timeline;
5. Approval & Actions;
6. Documents & Data, including upload, revisions, extraction state, and freshness.

Recommended sidebar: Overview, Recovery Cases, Documents & Data. Place Evidence
Review, Recovery Scenarios, and Approval & Actions inside the selected case as
tabs, with audit history and agent/tool activity available in the case.

The functional local web slice now implements this navigation using plain
HTML/CSS/JavaScript, a Python standard-library HTTP adapter, and SQLite persistence
(ADR-007). The user explicitly prioritizes functionality; visual polish is
deferred. Documents & Data currently supports corpus browsing, not upload or
runtime extraction. The local investigation remains a Python workflow with mock
retrieval. As of 2026-10-22 an explicit OpenAI advisory review is live-connected
in Agent Workflow; this does not perform document extraction or replace the
local Evidence Specialist. The viewer/replay is not an executable flow editor.

The five review views below remain the original detailed UI guidance.

Recommended five primary views:

## View 1 — Disruption / Exposure

Show:

```text
critical material
current usable stock
daily/projected consumption
original ETA
depletion date
affected orders
```

Example:

```text
CRITICAL MATERIAL EXCEPTION

BRG-001

Available Stock       300
Consumption / Day     100
Original ETA          Day 21

Projected Depletion   Day 3
Orders Exposed        4
```

---

## View 2 — Recovery Discovery

Show the search hierarchy and results:

```text
Network stock        none
Approved source      none
Approved equivalent  none
Alternate BOM        none
Valid deviation      none

Unqualified candidates:
Candidate A
Candidate B
Candidate C
```

This view demonstrates that the system does not jump prematurely to unqualified alternatives.

---

## View 3 — Evidence Matrix

This is likely the most important technical review view.

Example:

| Requirement | Candidate Value | Evidence | Status |
|---|---:|---|---|
| Bore = 25 mm | 25 mm | Datasheet Rev2 p.2 | MATCH |
| Dynamic load ≥ 14 kN | 16 kN | Datasheet Rev2 p.3 | MATCH |
| Lubricant at operating temperature | — | No applicable evidence | UNKNOWN |
| Plant qualification release | Not released | QMS | BLOCKED |

---

## View 4 — Recovery Timeline / Qualification Graph

Show candidate arrival vs actual readiness.

Example concept:

```text
DAY             1    2    3    4    5
Stock           ███████████
                         ↑
                     depletion

Candidate ETA        ●

Qualification             █████

Engineering                    ●
Quality                        ●

Usable                            ●
```

Primary message:

```text
Candidate arrives before shortage,
but qualification completes after depletion.
```

---

## View 5 — Approval / Action

Show:
- selected recovery scenario;
- unresolved conditions;
- required role;
- approval button;
- action receipt;
- production release status.

Example:

```text
Selected Recovery:
Original Expedite + Temporary Resequencing

Candidate A:
Qualification path not ready before depletion

[Approve Qualification Task]
[Request Revision]

Production Release: BLOCKED
```

---

# 23. Suggested Monorepo Structure

`[CURRENT DECISION]`

```text
material-continuity/
│
├─ apps/
│  └─ web/
│     ├─ src/
│     ├─ public/
│     └─ tests/
│
├─ services/
│  ├─ recovery-supervisor/
│  ├─ evidence-specialist/
│  └─ action-adapter/
│
├─ core/
│  ├─ exposure/
│  ├─ recovery-options/
│  ├─ requirements/
│  ├─ qualification/
│  ├─ simulation/
│  ├─ approval/
│  └─ case-state/
│
├─ data/
│  ├─ fixtures/
│  │  ├─ materials/
│  │  ├─ bom/
│  │  ├─ production-orders/
│  │  ├─ purchase-orders/
│  │  ├─ suppliers/
│  │  └─ qualification/
│  │
│  └─ documents/
│
├─ infrastructure/
│  └─ aws/
│
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ acceptance/
│
├─ docs/
│  ├─ architecture/
│  ├─ decisions/
│  └─ demo/
│
├─ scripts/
├─ .env.example
├─ README.md
├─ PROJECT_CONTEXT.md
└─ LICENSE
```

This file should be saved as:

```text
PROJECT_CONTEXT.md
```

at repository root.

---

# 24. Team Workstream Split

`[IMPLEMENTATION]`

For a 3-person team, divide by functional dependency rather than rigid frontend/backend/AI silos.

## Person 1 — Decision Engine

Own:
- synthetic ERP/QMS data;
- `getExposure`;
- `findRecoveryOptions`;
- qualification timing;
- recovery simulation;
- scenario ranking.

## Person 2 — Agent + Evidence

Own:
- S3;
- Knowledge Base;
- Bedrock;
- Evidence Specialist;
- Recovery Supervisor;
- tool-calling integration;
- provenance output.

## Person 3 — Case + Approval + UI

Own:
- recovery-case state;
- case versioning;
- approval model;
- action adapter;
- frontend;
- audit/event timeline.

### Integration rule

Do not wait until all three workstreams are "finished."

Integrate continuously around the canonical demo scenario.

---

# 25. Recommended Build Order

`[CURRENT DECISION]`

Do **not** start by building the agent.

Recommended sequence:

## Phase 0 — Environment / Architecture Validation

- [ ] Create GitHub organization.
- [x] Create monorepo.
- [x] Add `PROJECT_CONTEXT.md`.
- [x] Add `.gitignore`.
- [x] Add `.env.example`.
- [ ] Confirm AWS account.
- [ ] Confirm AWS Region.
- [ ] Verify service availability.
- [x] Choose local web MVP stack (ADR-007); public deployment stack remains open.
- [x] Define local run command.

## Phase 1 — Canonical Scenario + Synthetic Data

- [x] Lock one delayed-bearing exposure scenario.
- [x] Define original bearing.
- [x] Define current stock.
- [x] Define production demand.
- [x] Define delayed original receipt.
- [x] Define Candidate A.
- [x] Define Candidate B hard mismatch.
- [x] Define Candidate C / optional third path.
- [x] Define 2 BOMs.
- [x] Define 10 production orders.
- [x] Define supplier availability.
- [x] Define qualification test calendar.
- [x] Define 12 documents.

## Phase 2 — Deterministic Core

- [x] Implement `getExposure`.
- [x] Unit-test stock depletion.
- [x] Implement `findRecoveryOptions`.
- [x] Implement requirement normalization.
- [x] Implement `compareRequirements`.
- [x] Unit-test MATCH.
- [x] Unit-test MISMATCH.
- [x] Unit-test UNKNOWN.
- [x] Implement qualification dependency graph.
- [x] Implement `simulateRecovery`.
- [x] Compare three recovery scenarios.

## Phase 3 — Recovery Case

- [x] Define recovery-case schema.
- [x] Implement case creation.
- [x] Implement case updates.
- [x] Implement version increment.
- [x] Store source versions.
- [x] Store evidence matrix.
- [x] Store simulation results.
- [x] Store approvals.
- [x] Store action receipts.

## Phase 4 — Evidence Pipeline

- [ ] Upload synthetic docs to S3.
- [ ] Create Knowledge Base.
- [ ] Validate retrieval.
- [ ] Extract structured evidence from live Knowledge Base retrieval.
- [x] Define and validate the structured evidence extraction contract.
- [x] Preserve revision/page/source.
- [x] Connect structured evidence output to deterministic comparison.
- [x] Ensure unsupported evidence remains UNKNOWN.

## Phase 5 — Evidence Specialist

- [x] Define system prompt / role.
- [x] Define structured output schema.
- [x] Add retrieval tool interface and local mock adapter.
- [x] Add requirement-mapping workflow.
- [x] Add evidence-gap detection.
- [x] Add qualification-procedure retrieval.
- [x] Test with Candidate A.
- [x] Test with Candidate B.

## Phase 6 — Recovery Supervisor

- [x] Define supervisor role.
- [x] Expose controlled tools.
- [x] Implement recovery branching.
- [x] Maintain case state.
- [x] Call Evidence Specialist only when needed.
- [x] Call deterministic tools for all calculations.
- [x] Produce recovery summary.

## Phase 7 — Approval Gate

- [x] Define roles.
- [x] Define allowed actions by role.
- [x] Implement case hash.
- [x] Implement approval expiry.
- [x] Implement stale-case detection.
- [x] Implement source-freshness check.
- [x] Implement idempotency.

## Phase 8 — Action Adapter

- [x] Implement `createQualificationTask`.
- [x] Generate mock QMS identifier.
- [x] Record action receipt.
- [x] Prevent duplicate action.
- [x] Keep production release blocked.

## Phase 9 — UI

- [x] Disruption view.
- [x] Recovery options view.
- [x] Evidence matrix.
- [x] Qualification/recovery timeline.
- [x] Approval/action view.
- [x] Agent/tool timeline.
- [x] Stale approval visualization.
- [x] Persistent local case/approval/task storage and server-side demo sessions.
- [x] Read-only document corpus with PDF page links.
- [x] Explicit OpenAI advisory review and separately persisted review history.
- [x] Interactive read-only Agent Workflow canvas/list, node inspector and replay.
- [ ] Document upload and actual extraction/revision workflow.
- [ ] Visual polish and broader responsive/a11y verification.

## Phase 10 — Event / Observability

- [ ] EventBridge trigger.
- [ ] Event deduplication.
- [ ] CloudWatch logging.
- [ ] Agent/tool traces.
- [ ] Error-state logging.

## Phase 11 — Acceptance Demo

- [ ] Run canonical scenario end-to-end.
- [ ] Hard mismatch candidate rejected.
- [ ] Missing evidence remains UNKNOWN.
- [ ] Qualification timing extends past shortage.
- [ ] Recovery scenarios compared.
- [ ] Human approves qualification task.
- [ ] QMS task receipt generated.
- [ ] Production release remains blocked.
- [ ] Evidence revision changes.
- [ ] Case version increments.
- [ ] Previous approval becomes invalid.
- [ ] Duplicate action is blocked.

---

# 26. Current Progress Tracker

Update this section after every meaningful work session.

## Overall status

```text
Project phase: FUNCTIONAL LOCAL WEB MVP
Proposal: COMPLETE
Hackathon qualification: FINAL STAGE
GitHub strategy: DECIDED — one organization, one monorepo
Implementation: BACKEND-CONNECTED REVIEW UI + SQLITE + DEMO AUTH + INTERACTIVE WORKFLOW VIEWER + EXPLICIT OPENAI REVIEW COMPLETE LOCALLY; document ingestion/extraction and cloud remain pending
```

## Progress table

| Area | Status | Notes |
|---|---|---|
| Proposal | DONE | Submitted and passed to final stage |
| Project naming | DONE | Material Continuity |
| GitHub organization strategy | DONE | One org |
| Repository strategy | DONE | One monorepo |
| Canonical demo flow | DEFINED | Based on proposal acceptance scenario |
| Synthetic dataset | DONE | Material, stock, 2 BOMs, 10 production orders, delayed receipt, Candidate A/B/C, approved paths, suppliers, fallbacks, requirements, evidence, qualification tasks, resource calendars, and 12-document corpus defined |
| Deterministic exposure engine | DONE | Typed dependency-free Python engine, JSON loader, CLI, and 10 passing tests; canonical shortage is 2026-10-04 |
| Recovery option discovery | DONE | Ordered deterministic search covers network stock through resequencing; approved sufficiency stops candidate escalation; 6 dedicated tests pass |
| Requirement comparison | DONE | Typed evidence/provenance, deterministic unit conversion, revision/applicability checks, MATCH/MISMATCH/UNKNOWN/BLOCKED, and canonical Candidate A/B decisions; 14 dedicated tests pass |
| Qualification graph | DONE | Validated DAG, sequential/parallel scheduling, timezone-aware resource calendars, critical path, and unresolved timing propagation; Candidate A completes 2026-10-07T02:00Z |
| Recovery simulation | DONE | Deterministic timing, quantity coverage, order exposure, cost, unresolved conditions, and non-authorization across three canonical scenarios; 8 dedicated tests pass |
| Recovery-case versioning | DONE | Immutable typed snapshots, canonical SHA-256 hash chain, no-op detection, source-change increments, and version-bound approval/action storage; 9 dedicated tests pass |
| Approval gate | DONE | Typed principals/roles/actions; fail-closed identity, scope, expiry, case version/hash, source freshness, and idempotency validation; 11 dedicated tests pass |
| Action adapter | DONE | Approval-gated mock QMS qualification task, deterministic identifier, version-bound receipt, duplicate-write prevention, and explicit production-release block; 9 dedicated tests pass |
| AWS access validation | BLOCKED | Local validation attempted 2026-09-29; AWS CLI/SDK, Region, credentials/profile, and resource IDs are unavailable |
| S3 document corpus | BLOCKED | Twelve local PDFs and deterministic manifest are ready; S3 upload requires hackathon AWS access |
| Bedrock Knowledge Base | TODO | P1 |
| Evidence pipeline contract | DONE | Typed extraction boundary preserves provenance, excludes unsupported claims, and feeds the deterministic comparison engine; 8 dedicated tests pass |
| Evidence Specialist | LOCAL DONE | Guardrailed role prompt, typed output, replaceable retrieval interface, fixture-backed adapter, requirement mapping, gap/procedure detection, and Candidate A/B branches; live Bedrock adapter pending |
| Recovery Supervisor | LOCAL DONE | Guardrailed role, controlled fixture-backed tool interface, approved-path-first branching, conditional Evidence Specialist calls, case creation, tool trace, and structured summary; live AgentCore runtime pending |
| OpenAI inference adapter | WEB LIVE VERIFIED | Existing key and gpt-5.4-mini; explicit cost-acknowledged review via web verified (8 calls); local provider now openai; no automatic calls; full reliability/evaluation pending |
| UI | LOCAL FUNCTIONAL | Overview, case detail tabs including Agent Workflow, evidence/citations, scenarios/task schedule, approval/receipt/blocked reasons, history and trace, read-only Documents & Data |
| Interactive agent workflow | LOCAL DONE | User-confirmed n8n-like viewer, not editor: node inspector, dotted canvas, zoom/pan, keyboard/list alternative, replay; grouped local map separate from real OpenAI tool order; desktop/mobile browser verified |
| Advisory review history | LOCAL DONE | Separate SQLite ai_reviews table restores latest completed review without paid rerun; old hash/source state marks archive; decision/approval/task state unchanged |
| Web API and persistence | LOCAL DONE | Standard-library HTTP adapter; SQLite aggregate/history, scoped approvals and mock tasks; serial read/check/write transactions and unique target keys prevent concurrent duplicate writes |
| Authenticated web identity | LOCAL DEMO DONE | Password-verified demo users, server-owned roles, expiring opaque HttpOnly cookie sessions, CSRF/origin checks; enterprise SSO/public deployment auth not implemented |
| Runtime PDF ingestion | TODO | Corpus is browsable; upload, new document versions, and actual runtime extraction remain pending |
| EventBridge | TODO | P2 |
| Observability | TODO | P2 |
| SAP live integration | OUT OF MVP | Mock adapter is sufficient |

---

# 27. Session Progress Log

Append new entries; do not overwrite old ones.

## 2026-10-22 — Interactive workflow viewer and explicit OpenAI web review

### Completed

- User approved OpenAI web activation and requested n8n-like interactive agent-workflow explanation. Confirmed scope: viewer, node details and replay, not an editor that changes executable workflows or approval rules.
- Added the Agent Workflow case tab with an existing-system light canvas, connected nodes, source selector, node inspector, readable backend outcomes and expandable context/output. No graph/UI dependency was added.
- Separated a grouped local case-stage map (including fixture Evidence Specialist and human/mock action history) from actual recorded OpenAI tool order. Both retain explicit synthetic data / no runtime PDF-extraction limits.
- Added drag/keyboard pan, zoom/fit, previous/next and timed replay, plus a keyboard-accessible list that is the default on small screens. Replay does not call tools or consume credits.
- Added an explicit per-request cost/data-transfer acknowledgement, pending/error/configuration/freshness states and advisory disclaimer. Pending requests show no fabricated per-tool progress; failed runs are not yet persisted as node traces.
- Enabled provider=openai in the existing ignored local configuration without displaying or rewriting the existing API key. New-install examples remain opt-in/fixtures by default.
- Persisted completed review payloads in a separate SQLite ai_reviews table, not decision snapshots or approvals. Case view restores the latest review and marks old source/hash state as archived. Archived graphs use their original facts.
- Browser-initiated live review succeeded with gpt-5.4-mini: 8 calls, reported 30,372 input / 491 output tokens. Refresh restored the result without issuing a second paid review. Existing case version/hash and mock approval/task were preserved.
- Verified browser node selection, inspector, list/canvas toggle, zoom, keyboard pan, replay and persisted result. Captured 1126px desktop and 390px mobile; document scrollWidth matched viewport width at both sizes; restored normal viewport afterwards.
- All 141 Python tests and 10 dependency-free Node workflow tests pass; JS syntax checks pass. The mechanical design detector returned [] in degraded regex mode only (parsers absent); no full automated accessibility/contrast certification is claimed.
- Fixed the independent review's mobile replay finding: advancing/replaying keeps the selected node visible inside its own list without scrolling the whole page. Added three regression tests and verified the final node visible with unchanged page scroll position.
- Impeccable guided the scoped canvas addition and independent finish review. Final verdict: ship for the two scored fixes (mobile replay visibility and accurate product/design documentation), both resolved. This is not a full accessibility certification. User approved merging the workflow guidance into DESIGN.md without replacing the incumbent design; a documenter preserved those rules and added the actual component sidecar.

### Limits and next action

- Viewer is read-only; it cannot add/reorder executable tools, authorize tasks or change backend comparisons. This does not complete a live LLM Evidence Specialist, ingestion/retrieval, public hosting or AWS proposal infrastructure.
- Next: controlled PDF upload, immutable revisions, real page-aware extraction and ingestion-driven evidence/case updates. Continue to prioritize functionality before broader visual polish.

---

## 2026-10-22 — First live OpenAI review verified

### Completed

- User confirmed the existing API key/model had been entered locally and authorized the planned controlled connection test. Read configuration metadata only; never displayed or rewrote the key.
- Verified the configured model is `gpt-5.4-mini`. The persisted provider remains `fixtures`; used an in-memory `openai` override for this single manual smoke test only.
- The initial sandbox attempt failed at the network transport layer before an API response. Following the OpenAI troubleshooting workflow, reran the actual bounded review with approved network access; it succeeded.
- Reviewed persisted synthetic CASE-001 Version 1 with the real Responses API: exposure, approved-path discovery, three candidate evidence lookups, qualification dependencies, recovery scenarios, then structured completion (8 calls).
- Reported usage: 30,109 input tokens and 579 output tokens across the review. This was a real API call sequence, not an offline test; no monetary cost is inferred here.
- Rechecked the case hash and source fingerprints after inference. The test did not mutate decision state, approvals, action receipts or production-release authority. No model output was stored as technical evidence.
- Updated current tracker and README to distinguish this successful smoke test from the offline suite and from a full live-agent/PDF/cloud implementation.

### Limits and next action

- One successful manual review verifies this key/model/network path at test time, not ongoing quota, availability or production reliability. The configuration-status command still does not make a network call or persist connection verification.
- The normal application remains in fixture mode and its existing investigation stays deterministic/fixture-backed. No automatic paid calls or permanent provider changes were enabled.
- Next: add the explicit case-review UI entry with loading/error/advisory states, enable OpenAI deliberately for web use, then continue controlled PDF ingestion and page-aware extraction.

---

## 2026-10-22 — Optional OpenAI read-only review integration

### Completed

- Re-read this handoff completely and compared the submitted three-page proposal with current code/tracker before implementation.
- User explicitly requested preparing OpenAI integration using their existing API key; no new key was created. User confirmed the key is not yet stored locally. No real credential was read, displayed or written.
- Added a dependency-free, backend-only Responses API transport with explicit opt-in provider/model configuration, fixed HTTPS endpoint, redirect blocking, `store: false`, bounded HTTP/context/output, sanitized errors and no automatic retries.
- Added allowlisted optional `.env.local` loading with process-environment priority, expanded Git ignores for local env variants, and prepared a blank ignored local configuration for the user to fill. No default model or automatic paid startup call is assumed.
- Added bounded model-selected read-only review tools to the existing Recovery Supervisor package. They read an immutable backend-calculated case snapshot; prerequisites enforce exposure and approved paths before candidate investigation. Hard-rejected candidates cannot obtain qualification plans.
- Final model prose is advisory and separate from unchanged deterministic facts. The adapter exposes no authorization, procurement, production-release or task-write tool. It does not replace the fixture-backed investigation or perform PDF extraction.
- Added authenticated/CSRF-protected `POST /api/cases/{id}/ai-review`, redacted authenticated `GET /api/llm/status`, and a no-network `python -m services.llm` configuration check.
- Do not hold a SQLite write transaction during inference. Check case version/hash and source freshness before and after the call; stale results are discarded. AI output is not persisted into case versions, approvals or action receipts.
- Added 23 offline transport, configuration, tool-order, malformed-output, role/CSRF, freshness, concurrency and no-mutation tests. All 139 repository tests pass. The initial sandbox run hit Windows temporary-directory permissions; the full rerun with local temp/socket access passed. `git diff --check`, Git-ignore verification for `.env.local`, and the no-network configuration check pass.

### Limits and next action

- Existing key and an API-accessible model still need local configuration. No actual OpenAI request, quota/model-access check, live reliability claim or credit usage has occurred.
- This is backend/API-first preparation, not a new chatbot, a completed LLM Evidence Specialist, automatic PDF parsing, or a replacement for the proposal's AWS services. The browser does not yet expose an AI review button.
- Next: configure the existing key/model locally, verify one controlled request, add the case-review UI entry, then implement controlled PDF ingestion/page-aware extraction and feed it through the existing evidence contract.
- AWS hosting/retrieval/event infrastructure and full proposal acceptance/evaluation remain open. See ADR-008 for the limited provider decision.

---

## 2026-10-13 — Functional local web review workflow

### Completed

- Read the feedback supplied from the earlier ChatGPT conversation and followed the user's functional-first direction, deferring visual refinement.
- Added a plain browser UI and a Python standard-library HTTP adapter around existing domain/agent functions without new third-party runtime dependencies.
- Implemented Overview/case listing and case detail tabs for summary/discovery, evidence, recovery scenarios/qualification schedule, and approvals/actions.
- Added allowlisted PDF serving with page-specific citations and read-only document metadata/checksum browsing.
- Added SQLite persistence for complete immutable case history, approvals, scoped qualification targets, tasks, receipts, users, and sessions using a lossless allowlisted JSON codec.
- Implemented password-verified local demo login with server-authoritative identity/roles, expiring HttpOnly/SameSite cookies, CSRF tokens, origin/host checks, and logout.
- Enforced optimistic reviewed version/hash checks on mutations; browser role, identity, arbitrary task targets, and idempotency keys are not accepted as authorization.
- Wrapped authorization/action creation in SQLite read/check/write transactions, with a unique per-case-version/candidate/requirement task key so parallel requests and separate approvals cannot create duplicate tasks.
- Added input fingerprints for the local synthetic dataset/PDF corpus, detecting source-byte changes even when revision strings are unchanged.
- Added re-investigation preserving approvals/actions/history, no-op version behavior, stale approval blocking, and conservative source-change blocking before action.
- Tied substitute scenario readiness to the current qualification graph and blocked substitute coverage if a refreshed candidate develops a hard mismatch.
- Verified the browser flow: login, case/evidence/scenarios, qualification approval, mock task/receipt, page reload persistence, documents, and planner role restrictions.
- Added 18 HTTP/persistence acceptance tests; all 116 repository tests pass. Browser JavaScript syntax check passed.
- Impeccable's mechanical detector returned no regex findings but ran in degraded mode because parser modules are absent; no comprehensive visual/a11y pass is claimed.
- Updated README with run/login instructions, API contracts, persistence behavior, and explicit synthetic/local-only limitations.

### Limits and next action

- This server binds localhost only. Shared demo credentials are for the synthetic local workflow; public hosting, TLS/SSO and enterprise identities remain pending.
- No new live LLM, cloud adapter, scraper, scheduler, document upload, or actual runtime PDF extraction is implemented in this slice.
- Next: add controlled document upload, immutable document revisions, actual page-aware extraction, and case re-investigation driven by ingested evidence.
- Preserve existing core decisions and resolve live model/provider access later; improve visual design after the functional flow is complete.

---

## 2026-10-13 — Web MVP planning and ChatGPT handoff

### Completed

- Verified Recovery Supervisor commit `d090dfb` is on `main` and synced with the organization repository before this documentation update.
- Re-ran the existing test suite; all 98 tests pass.
- Recorded the user's decision to skip a separate standalone CLI demo runner and proceed directly to the UI with the canonical flow demonstrated through the web application.
- Documented the proposed six functional areas and compact three-menu navigation.
- Documented the proposed data strategy: controlled document ingestion, runtime retrieval, and current-source checks for volatile operational data; scraper targets and sync cadence remain undecided.
- Clarified implementation limits: local agent workflows use prepared fixtures, no live LLM invocation or actual runtime PDF extraction exists, and HTTP API/persistence/real user authentication remain pending.
- Recorded that SAP access verification was deferred by the user; no credentials were fetched and no cloud-provider architecture change was made.
- Created `CHATGPT_HANDOFF_2026-10-13.md` as a self-contained progress and planning handoff for the earlier ChatGPT conversation.

### Next recommended action

1. settle the minimum web/API/persistence contracts and implementation stack with a concrete technical rationale;
2. build a backend-connected case review UI using existing engines and local adapters;
3. connect approval/action and source-revision changes to persistent case state with authenticated reviewer identity;
4. add actual document ingestion/extraction and freshness visibility;
5. verify and connect cloud inference/retrieval when account access and provider decisions are available.

---

## 2026-09-29 — Local Recovery Supervisor

### Completed

- Added the Recovery Supervisor package with an explicit orchestration-only role prompt and human-release guardrails.
- Added typed workflow requests, candidate assessments, tool traces, scenario summaries, and recovery summaries.
- Added a controlled tool protocol plus a fixture-backed implementation that invokes the existing deterministic exposure, recovery-option, qualification, simulation, case-state, and source-version modules.
- Enforced ordered branching: calculate exposure, exhaust approved paths, and call the Evidence Specialist only when approved recovery is insufficient.
- Added a no-exposure early exit that avoids unnecessary recovery and evidence calls.
- Added an approved-recovery branch that skips the Evidence Specialist entirely.
- Investigated all surfaced unqualified candidates in the canonical branch, rejected Candidate B for its hard mismatch, and preserved Candidate A/C as conditional.
- Built Case Version 1 from the orchestrated outputs while preserving production release as unauthorized.
- Produced a structured summary for 700 exposed units across 7 orders and three deterministic recovery scenarios.
- Added five unit tests and one canonical integration test.
- Verified all 98 repository tests pass.

### Next recommended action

1. add a local end-to-end demo runner that connects supervisor output to human approval and the mock QMS action;
2. demonstrate qualification-task creation while production release remains blocked;
3. revise Candidate A evidence from revision 2 to 3 and show the previous approval becomes stale;
4. demonstrate duplicate action blocking in the same canonical flow.

---

## 2026-09-29 — Mock-backed Evidence Specialist

### Completed

- Added the Evidence Specialist package with an explicit role prompt that preserves the boundary: retrieve and interpret evidence, use deterministic tools for comparison, and never authorize release.
- Added typed investigation requests, structured results, evidence gaps, qualification-procedure references, and retrieval traces.
- Added a replaceable retrieval protocol so the local mock adapter can later be exchanged for Bedrock Knowledge Base retrieval without changing the workflow contract.
- Added fixture-backed candidate evidence and qualification-procedure retrieval aligned to the PDF corpus revisions and pages.
- Reused the structured evidence pipeline and deterministic comparison engine for all requirement decisions and unit logic.
- Implemented gap detection for `UNKNOWN` and `BLOCKED` requirements and linked relevant qualification procedures.
- Stopped procedure lookup for a candidate with a hard mismatch so qualification cannot be presented as a cure for dimensional incompatibility.
- Verified Candidate A returns the lubricant-temperature and release gaps with the correct procedures.
- Verified Candidate B is rejected for `REQ-BORE-001` and does not proceed to qualification-procedure retrieval.
- Added five unit tests and one canonical integration test.
- Verified all 92 repository tests pass.

### Next recommended action

1. implement the Recovery Supervisor against the completed local tool interfaces;
2. exhaust approved recovery options before invoking the Evidence Specialist;
3. preserve recovery-case state and call deterministic simulation/qualification outputs rather than recalculating them;
4. produce a structured recovery summary for the local end-to-end demo.

---

## 2026-09-29 — Structured evidence pipeline contract

### Completed

- Added typed structured-extraction records with explicit support status, value/unit, applicability, confidence, and revision/page/location provenance.
- Added fail-closed preparation that excludes unsupported claims, missing values, and incomplete provenance before deterministic comparison.
- Connected accepted structured evidence directly to the existing requirement-comparison engine without adding a second comparison implementation.
- Preserved wrong-revision and conflicting-evidence behavior as `UNKNOWN`.
- Added canonical extraction fixtures for Candidate A and Candidate B aligned to the generated PDF page locations.
- Verified Candidate A bore/load remain `MATCH`, lubricant evidence remains `UNKNOWN`, and release remains `BLOCKED`.
- Verified Candidate B remains rejected for the hard 30 mm versus 25 mm bore mismatch.
- Added seven unit tests and one canonical integration test.
- Verified all 86 repository tests pass.

### Next recommended action

1. configure read-only hackathon AWS access and confirm the target Region and allowed services;
2. upload the twelve-document corpus to S3 and create the Bedrock Knowledge Base;
3. validate live retrieval returns document, revision, page, and location;
4. map the live extraction output into the completed evidence contract.

---

## 2026-09-29 — Approval-gated mock action adapter

### Completed

- Added a typed `createQualificationTask` command and structured result for the mock QMS action boundary.
- Required a current `AUTHORIZED` approval-gate decision before any mock write occurs.
- Restricted task creation to a known candidate with a requirement represented in its qualification plan; hard-rejected Candidate B fails closed.
- Generated deterministic mock QMS and action identifiers from case, candidate, requirement, and idempotency-key content.
- Appended a version/hash-bound action receipt without incrementing the decision-case version.
- Blocked duplicate execution before a second receipt can be created while preserving the first receipt for audit.
- Kept qualification-task creation explicitly separate from material release; every result returns `production_release_authorized: false`.
- Added eight unit tests and one canonical integration test covering success, deterministic IDs, stale/expired approval, hard mismatch, invalid plan target, wrong action type, and duplicate execution.
- Verified all 78 repository tests pass.

### Next recommended action

1. obtain/configure read-only hackathon AWS access, Region, and resource identifiers;
2. upload the verified document corpus to S3;
3. create the Bedrock Knowledge Base and validate document revision/page retrieval;
4. connect retrieved structured evidence to deterministic comparison before implementing the Evidence Specialist.

---

## 2026-09-29 — Deterministic approval gate

### Completed

- Added typed authenticated principals, approver roles, controlled actions, approval decisions, and explicit block reasons.
- Defined least-privilege role policy: Engineering and Quality may authorize qualification-task creation; Production Planning may authorize resequencing; no production-release action is exposed.
- Implemented fail-closed approval validation for exact approver identity, role/action scope, activation and expiry windows, current case version/hash, live source-version state, and unused idempotency key.
- Kept expected authorization failures as structured `BLOCKED` decisions while rejecting malformed requests such as naive timestamps and duplicate source IDs.
- Added direct source-freshness comparison that detects changed, added, or missing source versions before an action is attempted.
- Added ten unit tests and one canonical integration test.
- Demonstrated that a valid qualification-task approval becomes blocked after Candidate A evidence advances from revision 2 to revision 3.
- Verified all 69 repository tests pass.

### Next recommended action

1. implement the mock `createQualificationTask` action adapter;
2. require an `AUTHORIZED` approval-gate decision before the write;
3. generate a deterministic mock QMS identifier, append the action receipt, and keep production release blocked;
4. preserve idempotent replay behavior and test duplicate execution.

---

## 2026-09-29 — Synthetic evidence document corpus

### Completed

- Added twelve text-based synthetic PDF fixtures under `data/documents/`, covering candidate datasheets/certificate, Assembly A/B drawings, application requirements, qualification SOPs, supplier approval status, an expired deviation, and the Quality release procedure.
- Added explicit document IDs, revisions, effective dates, owners, synthetic-data classification, and stable `Page X of N` markers on every page.
- Preserved canonical evidence locations: Candidate A bore on page 2, load on page 3, and missing application-specific lubricant evidence on page 4; Candidate B bore on page 2, load on page 3, and lubricant suitability on page 4.
- Added a deterministic generator and SHA-256 manifest without adding an application runtime dependency.
- Added semantic validation for all 35 pages, including stable evidence fragments and provenance markers.
- Rendered and visually inspected all 35 pages; no clipping, overflow, or unreadable layout was observed.
- Added three dependency-free integration tests for corpus completeness, checksums, metadata, and unexpected PDFs.
- Verified all 58 repository tests pass.
- Attempted read-only AWS validation. It is blocked because the environment has no AWS CLI/SDK, configured Region/profile/credentials, Bedrock resource IDs, or S3 bucket configuration. No AWS resource was created or changed.

### Next recommended action

1. obtain/configure read-only hackathon AWS access and confirm Region, Bedrock, AgentCore, Knowledge Base, S3, Lambda, EventBridge, and CloudWatch availability;
2. upload the verified corpus to S3 and validate revision/page-aware retrieval;
3. while AWS access remains blocked, implement the P0 approval gate against the existing versioned recovery-case model;
4. connect retrieved structured evidence to the deterministic comparison engine.

---

## 2026-09-29 — Versioned recovery case

### Completed

- Added a typed recovery-case aggregate containing immutable decision versions plus separately stored approvals and action receipts.
- Assembled exposure, recovery discovery, Candidate A/B evidence decisions, Candidate A qualification graph, scenario simulation, and source versions into the canonical case.
- Implemented deterministic SHA-256 case hashes over canonical JSON decision content, case identity, version, and previous hash.
- Implemented immutable version chaining and explicit change reasons.
- Implemented no-op detection so unchanged decision content does not increment the case version.
- Implemented source-version change detection and changed-source reporting.
- Kept approvals and action receipts bound to exact case version/hash without incrementing the decision version when records are appended.
- Added validation for version/hash references, audit chronology, duplicate approval/action IDs, and duplicate action idempotency keys.
- Deliberately kept persistence backend selection open; the current implementation is a dependency-free immutable domain model with JSON-safe serialization.
- Added eight unit tests and one canonical integration test.
- Verified all 55 repository tests pass and compilation succeeds.
- Demonstrated the stale-approval story:
  - approval targets Case Version 1 / its exact hash;
  - Candidate A datasheet changes from revision 2 to revision 3;
  - case increments to Version 2 with a chained, different hash;
  - the previous approval remains auditable but no longer matches the current version/hash.

### Next recommended action

1. create the twelve-document local synthetic corpus with explicit revision/page markers;
2. validate AWS account, Region, Bedrock model, S3, and Knowledge Base availability;
3. upload the corpus to S3 and validate retrieval provenance;
4. connect retrieved structured evidence to the existing deterministic comparison engine.

---

## 2026-09-29 — Deterministic recovery simulation

### Completed

- Added explicit simulation fixtures for:
  - Candidate A plus qualification;
  - original-part expedite;
  - temporary production resequencing.
- Implemented deterministic `simulateRecovery()` using the exposure engine's affected orders and explicit shortage timestamp.
- Added per-order coverage allocation, remaining exposed quantity/order counts, recovery timing, delay after shortage, and incremental cost.
- Preserved unresolved readiness as `UNRESOLVED` without estimated completion or optimistic coverage.
- Enforced that substitute readiness cannot precede qualification completion.
- Kept feasibility separate from authorization; every simulated scenario returns `authorized_for_execution: false`.
- Added fail-closed validation for contradictory exposure state, duplicate scenario IDs, invalid quantities/costs, naive timestamps, and readiness before qualification completion.
- Added seven unit tests and one canonical integration test.
- Verified all 46 repository tests pass and compilation succeeds.
- Verified the canonical comparison:
  - Candidate A + qualification: ready `2026-10-07T02:00:00Z`, protects 400 units, leaves 300 units / 3 orders exposed, `PARTIAL`;
  - original expedite: ready at shortage, protects all 700 units, `FEASIBLE` but not authorized;
  - production resequencing: protects 200 units, leaves 500 units / 5 orders exposed, `PARTIAL`.

### Next recommended action

1. define the typed recovery-case schema;
2. implement case creation and immutable version snapshots;
3. store source versions, exposure, evidence matrix, qualification graph, and simulations;
4. increment the case version when decision-relevant source data changes.

---

## 2026-09-29 — Qualification dependency graph

### Completed

- Added Candidate A qualification task fixtures linking the missing lubricant-temperature evidence to:
  - candidate delivery;
  - temperature qualification test;
  - Engineering review;
  - Quality review;
  - qualification release.
- Added timezone-aware resource-calendar fixtures for the temperature lab, Engineering, and Quality.
- Implemented deterministic qualification DAG validation and topological scheduling.
- Implemented sequential and parallel task scheduling across working days, work-hour windows, weekends, and unavailable dates.
- Implemented critical-path derivation without losing dependencies across calendar wait periods.
- Preserved unknown timing with explicit `UNRESOLVED` states for missing durations, missing start conditions, and unavailable resource calendars.
- Added fail-closed checks for duplicate IDs, invalid calendars, missing predecessors, negative durations, naive timestamps, and dependency cycles.
- Added seven unit tests and one canonical fixture integration test.
- Verified all 38 repository tests pass and compilation succeeds.
- Verified Candidate A:
  - arrives `2026-10-02T02:00:00Z`;
  - completes its qualification path `2026-10-07T02:00:00Z`;
  - is therefore not ready by the `2026-10-04` shortage date.

### Next recommended action

1. implement deterministic `simulateRecovery()`;
2. compare Candidate A + qualification, original-part expedite, and production resequencing;
3. report ready date, exposed quantity/orders, incremental cost, feasibility, and unresolved conditions;
4. keep unresolved qualification completion explicitly non-feasible rather than estimating it.

---

## 2026-09-29 — Deterministic requirement comparison

### Completed

- Added application requirement fixtures for bore diameter, dynamic load, lubricant-temperature suitability, and plant qualification release.
- Added structured Candidate A/B evidence fixtures with document, revision, page, location, and applicability provenance.
- Implemented typed deterministic `compareRequirements()` behavior for `MATCH`, `MISMATCH`, `UNKNOWN`, and `BLOCKED`.
- Added deterministic unit normalization/conversion for MVP length, force, temperature, and speed units without introducing dependencies.
- Enforced fail-closed behavior for:
  - missing evidence;
  - incompatible units;
  - stale source revisions;
  - conflicting evidence;
  - non-applicable evidence;
  - malformed value types;
  - empty requirement sets.
- Added candidate-level decisions that reject hard mismatches while keeping missing evidence and unsatisfied release gates blocked.
- Added twelve unit tests and two canonical fixture integration tests.
- Verified all 30 repository tests pass and compilation succeeds.
- Verified the canonical decisions:
  - Candidate A: bore `MATCH`, load `MATCH`, lubricant evidence `UNKNOWN`, plant release `BLOCKED`;
  - Candidate B: bore `MISMATCH` with hard reject, load/lubricant `MATCH`, plant release `BLOCKED`.

### Next recommended action

1. define qualification task and resource-calendar fixtures;
2. implement the deterministic qualification dependency graph;
3. calculate sequential and parallel critical paths while preserving unresolved durations;
4. connect Candidate A's evidence gap to the required temperature test and review/release chain.

---

## 2026-09-29 — Deterministic recovery-option discovery

### Completed

- Added Candidate A, Candidate B, and Candidate C master fixtures plus supplier availability, ETA, quantity, quote, and source references.
- Added canonical recovery fixtures for:
  - network stock;
  - approved original source;
  - approved equivalent;
  - alternate BOM;
  - expired deviation;
  - original-part expedite;
  - production resequencing.
- Implemented typed, deterministic `findRecoveryOptions()` behavior with the required search order.
- Added quantity coverage across approved paths and early termination when approved options fully cover demand.
- Ensured unqualified candidates and fallbacks are surfaced only after timely approved paths are exhausted.
- Preserved availability versus readiness by reporting candidate ETA separately from approval status and by marking whether each option arrives by the need date.
- Added an auditable per-category search trace and fail-closed validation for duplicate IDs, invalid quantities/costs, and invalid request dates.
- Added five unit tests and one canonical fixture integration test.
- Verified all 16 repository tests pass, compilation succeeds, and the canonical search returns:
  - approved coverage: 0 of 700;
  - Candidate A/B: arrive by need date but remain unqualified;
  - Candidate C: arrives after need date and remains unqualified;
  - original expedite and production resequencing as non-authorized fallbacks.

### Next recommended action

1. add application requirement and candidate specification fixtures with source revision/page provenance;
2. implement deterministic unit normalization;
3. implement `compareRequirements()` for MATCH, MISMATCH, UNKNOWN, and BLOCKED;
4. prove Candidate B is rejected for the hard bore mismatch and Candidate A remains UNKNOWN for missing lubricant-temperature evidence.

---

## 2026-09-29 — Local bootstrap and deterministic exposure engine

### Completed

- Initialized the local Git monorepo.
- Added the recommended root scaffolding: `.gitignore`, `.env.example`, `README.md`, and `pyproject.toml`.
- Chose dependency-free Python 3.11 dataclasses and `unittest` for the first deterministic slice; no backend or frontend framework decision was made.
- Added the canonical local exposure fixtures:
  - one original bearing material with stock, allocation, and quality-hold quantities;
  - two effective BOM rows;
  - ten dated production orders;
  - one delayed receipt and one later confirmed receipt.
- Implemented deterministic `getExposure` behavior with:
  - usable-stock calculation;
  - confirmed time-phased receipts;
  - BOM-derived production consumption;
  - deterministic same-day priority ordering;
  - first-shortage detection;
  - affected-order quantities;
  - fail-closed validation for invalid stock, duplicate IDs, and ambiguous/missing BOM rows.
- Added a JSON-fixture CLI and JSON-safe structured output.
- Added nine unit tests and one fixture integration test covering exact depletion, receipts before/after shortage, zero stock, overlapping orders, unrelated products, repeat-call idempotence, duplicate IDs, and timestamp validation.
- Verified all 10 tests pass and the canonical fixture returns:
  - usable stock: 300;
  - shortage date: `2026-10-04`;
  - first affected order: `MO-004`;
  - affected orders: 7.

### Next recommended action

1. complete Candidate A/B/C and supplier-availability fixtures;
2. add network stock, approved-source/equivalent, alternate-BOM, and deviation fixtures;
3. implement deterministic `findRecoveryOptions()` in the required search order;
4. unit-test that approved recovery paths are exhausted before unqualified candidates are returned.

---

## 2026-09-28 — Project setup planning

### Completed

- Project proposal already completed.
- Team passed proposal screening and reached final stage.
- Project name confirmed as **Material Continuity**.
- GitHub organization naming discussed.
- Recommended organization/repository name: `material-continuity`.
- Decided to use one monorepo.
- Implementation order defined.
- Core architecture boundary defined:
  - LLM interprets/orchestrates;
  - deterministic code calculates/enforces;
  - humans authorize.

### Next recommended action

1. initialize local repository;
2. add this file as `PROJECT_CONTEXT.md`;
3. create repo folders;
4. lock synthetic demo dataset;
5. implement deterministic `getExposure()` before agent work.

---

# 28. Architecture Decision Records

Use this section for small ADRs.

## ADR-001 — Monorepo

**Status:** Accepted

**Decision:** Use one repository for web, agents, deterministic core, data, and infrastructure.

**Reason:** Team is small, system is tightly coupled, hackathon timeline rewards integration speed.

---

## ADR-002 — Deterministic calculations outside LLM

**Status:** Accepted

**Decision:** Stock depletion, numerical comparisons, qualification timing, scenario calculations, authorization checks, and idempotency are deterministic.

**Reason:** Reproducibility, auditability, proposal consistency, safety.

---

## ADR-003 — Two-agent architecture

**Status:** Accepted

**Decision:** Use:
1. Recovery Supervisor;
2. Evidence Specialist.

**Reason:** Matches proposal while avoiding unnecessary multi-agent complexity.

---

## ADR-004 — Human release authority retained

**Status:** Accepted

**Decision:** No autonomous BOM release, production release, or unrestricted purchasing.

**Reason:** Core safety and governance requirement.

---

## ADR-005 — Mock enterprise write for MVP

**Status:** Accepted

**Decision:** `createQualificationTask()` may produce a mock QMS task instead of live SAP write-back.

**Reason:** Proposal explicitly places live SAP write-back after MVP.

---

## ADR-006 — Canonical hash-bound case versions

**Status:** Accepted

**Decision:** Represent decision state as immutable recovery-case versions. Compute each `case_hash` using SHA-256 over canonical JSON containing the case ID, case version, previous case hash, and complete decision-relevant content. Store approvals and action receipts outside the version payload while binding each record to an exact case version/hash.

**Reason:** This provides reproducible hashes, an auditable version chain, no-op update detection, and stale-authorization visibility without causing an approval append to invalidate itself.

**Consequences:** Any change to decision content or tracked source-version records creates a new case version. Timestamp-only case access and approval/action appends do not. Persistence technology remains undecided and can store the same immutable domain model later.

---

## ADR-007 — Dependency-free local web adapter and SQLite persistence

**Status:** Accepted for the local synthetic web MVP, 2026-10-13

**Previous state:** Domain core and local agent workflows were available only as libraries/CLI/tests; HTTP, durable state, and web identity were open decisions.

**Decision:** Serve the initial functional browser UI with plain HTML/CSS/JavaScript and a localhost-only Python standard-library HTTP adapter. Persist immutable domain aggregates, approvals/action history, scoped task records, and demo sessions in SQLite. Store typed aggregates with an allowlisted lossless JSON codec rather than pickle. Derive actor roles from password-verified server sessions.

**Reason:** The user prioritizes working functionality and asks to avoid dependencies without a concrete technical reason. The existing Python core can be reused directly; stdlib SQLite provides durable local state and atomic read/check/write transactions without new packages or infrastructure. UI refinement and cloud integrations need not block the first review/action slice.

**Consequences:** The local app has functional review/approval/task creation and restart persistence. Per-target unique task keys plus serialized transactions prevent concurrent duplicate mock writes. The HTTP adapter is not a public production server; deployment will require reevaluating hosting, durable storage, TLS, identity, and operational requirements. AWS proposal commitments and core architecture remain unchanged. PDF upload/runtime extraction and live inference are still separate future integrations.

---

## ADR-008 — Optional OpenAI review adapter while AWS access is unavailable

**Status:** Accepted for interim local integration preparation, 2026-10-22; one manual live review verified on the same date.

**Previous state:** Local agent workflows used only fixture-backed adapters. AWS Bedrock/AgentCore remained the proposal target but access was not configured.

**Decision:** At the user's explicit request, add an optional OpenAI Responses adapter using the existing Python standard library. Require explicit provider opt-in, an existing user-owned API key, and an explicitly configured API model. First expose a bounded read-only review of existing immutable case snapshots through the Recovery Supervisor package and authenticated web API. Preserve the deterministic supervisor and all human approval/action boundaries. No new agent, SDK/framework dependency, arbitrary endpoint override, or enterprise write tool is introduced.

**Reason:** The user has OpenAI access and wants to prepare that integration before AWS availability is resolved. A narrow replaceable adapter enables actual model-selected read-only tool calls without redesigning the product or coupling numerical/authorization logic to an LLM.

**Consequences:** This is a limited local inference-provider deviation, not delivery of the AWS architecture promised in the proposal. Existing enterprise data and extracted evidence remain synthetic/prepared. AI prose is advisory, not verified evidence, and does not alter case hashes, approvals, receipts or release status. Calls are explicit, bounded, can incur charges, and send synthetic case facts to OpenAI; no silent fallback or startup call occurs. Manual and browser-initiated reviews succeeded and the user explicitly approved local web activation. New-install examples still default to fixtures. Document extraction, full live-agent evaluation and AWS deployment remain pending.

---

## ADR-009 — Read-only workflow viewer and separate advisory execution history

**Status:** Accepted for the local web MVP, 2026-10-22.

**Previous state:** Case activity was a table, and OpenAI review output was returned through the API without durable advisory history.

**Decision:** Render an n8n-like inspectable node canvas using native DOM/SVG and existing CSS/JavaScript. Maintain separate grouped local-case and recorded OpenAI-trace views. Keep model advisories and their original snapshot/usage in an independent SQLite table; the case view annotates freshness against current hash/source state. Preserve core case versions and approvals unchanged.

**Reason:** The user explicitly wants an interactive explanation/replay, not an editable agent workflow. Persisted advisories make actual tool order inspectable after refresh without another paid request. No third-party graph library or orchestration redesign is required.

**Consequences:** Zoom/pan, node details, list mode and replay are presentation controls only. They never execute tools, reorder the agent, authorize writes or constitute live-streamed progress. Archived reviews retain their original facts and are labelled outdated. Model output is not promoted to engineering evidence. Failed-run per-node traces and document ingestion remain future work.

---

# 29. Testing Strategy

## 29.1 Unit Tests

Must cover:

### Exposure

- exact depletion date;
- receipts before shortage;
- receipts after shortage;
- zero stock;
- overlapping production orders;
- duplicate event input.

### Requirement Comparison

- exact match;
- min-bound match;
- max-bound match;
- mismatch;
- missing evidence;
- incompatible units;
- convertible units;
- wrong document revision;
- conflicting evidence.

### Qualification Timing

- sequential tasks;
- parallel tasks;
- missing completion time;
- unavailable resource calendar;
- qualification before shortage;
- qualification after shortage.

### Approval

- valid role;
- invalid role;
- expired approval;
- stale case version;
- changed case hash;
- duplicate idempotency key.

---

## 29.2 Integration Tests

- evidence extraction → deterministic comparison;
- supervisor → tool calls → recovery case;
- recovery case → approval gate;
- approval gate → action adapter;
- source update → case version increment;
- version increment → approval invalidation.

---

## 29.3 Acceptance Tests

The final system must successfully demonstrate:

```text
delay event
→ exposure calculation
→ no timely approved option
→ candidate discovery
→ hard mismatch rejection
→ UNKNOWN evidence gap
→ qualification timing
→ scenario comparison
→ human approval
→ mock QMS action
→ production release remains blocked
→ source revision change
→ approval invalidation
```

---

# 30. Pilot Metrics

`[PROPOSAL]`

These are **pilot targets**, not achieved results.

Do not present them as proven outcomes.

## Time to reviewable package

Measure:

```text
event → complete reviewable evidence package
```

Target:

```text
at least 50% lower median than manual baseline
```

## Time to approved decision

Measure:

```text
event → recorded approved decision
```

Target:

```text
lower, without higher reviewer effort
```

## Critical-gap detection

Measure:

```text
seeded missing/contradictory requirements detected
```

Target:

```text
100% of seeded critical gaps flagged
```

## Evidence traceability

Measure:

```text
supported MATCH rows with valid source/revision/location
```

Target:

```text
100%
```

No unsupported MATCH.

## Action integrity

Measure unauthorized/stale/duplicate actions.

Target:

```text
zero prohibited or duplicate writes
```

## Production exposure

Measure simulated:

```text
unserved units / late orders
```

Target:

```text
lower simulated exposure
```

Real production benefit requires a plant pilot and must not be claimed from the MVP.

---

# 31. Important Messaging Rules for Demo / Pitch

## Do say

```text
"The candidate is available, but it is not yet ready for assembly."
```

```text
"We calculate when the candidate becomes usable after evidence, testing, and release dependencies."
```

```text
"Missing evidence remains UNKNOWN rather than being inferred as compatible."
```

```text
"The agent coordinates the investigation, while deterministic services calculate constraints and humans retain release authority."
```

```text
"Our pilot target is at least a 50% reduction in median time to a reviewable package."
```

## Do not say

```text
"Our system automatically approves replacement parts."
```

```text
"Our agent decides whether a bearing is safe."
```

```text
"We reduce decision time by 50%."
```

unless this has actually been measured.

```text
"This is the first system in the market to do this."
```

The proposal intentionally does **not** claim market-first capability.

---

# 32. Innovation Positioning

`[PROPOSAL]`

The proposal explicitly acknowledges overlapping capabilities in:
- SAP Manufacturing Assistant;
- SAP Planning Assistant;
- SAP Product Design Assistant;
- generic procurement agents;
- manufacturing control towers;
- RAG systems;
- change-management / scenario agents.

The contribution is narrower:

> **Connect application-specific evidence and qualification dependencies to a material-shortage deadline, with version-bound execution controls.**

Do not exaggerate the novelty claim.

---

# 33. Scope Guardrails

When an AI coding agent proposes a feature, classify it.

## P0 — Directly required for canonical demo

Examples:
- exposure calculation;
- requirement comparison;
- qualification timing;
- evidence provenance;
- case versioning;
- approval gate.

## P1 — Important for judging / architecture credibility

Examples:
- Bedrock retrieval;
- supervisor orchestration;
- polished UI;
- action receipt;
- agent tool trace.

## P2 — Useful but non-critical

Examples:
- EventBridge;
- richer observability;
- advanced filters;
- extra dashboards.

## P3 — Post-MVP

Examples:
- live SAP write-back;
- supplier onboarding;
- complex CAD/drawing interpretation;
- advanced optimization;
- production-scale permissions model;
- multiple plants;
- real physical validation.

If a P2/P3 feature threatens P0 completeness, defer it.

---

# 34. Security / Safety Checklist

- [ ] Least-privilege IAM.
- [ ] No unrestricted procurement tool.
- [ ] No unrestricted BOM release tool.
- [ ] Retrieved content is data, not authorization.
- [x] Approval tied to case version.
- [x] Approval tied to action scope.
- [x] Approval expiry enforced.
- [x] Stale approvals fail closed.
- [x] Duplicate writes blocked.
- [x] Action receipt logged.
- [ ] Tool errors bounded.
- [ ] Retrieval retries bounded.
- [ ] Missing sources escalate to human review.
- [ ] Agent cannot fabricate missing evidence as MATCH.

---

# 35. Engineering Conventions

`[IMPLEMENTATION]`

Recommended:

## Typed schemas

Use typed request/response schemas for:
- tools;
- evidence rows;
- recovery cases;
- approval records;
- action receipts.

Prefer Pydantic / Zod / equivalent.

## Determinism

All deterministic functions should:
- accept explicit inputs;
- return structured outputs;
- avoid hidden global state;
- be unit-testable.

## Timestamps

Use ISO 8601 UTC internally.

Convert to local display only in UI.

## IDs

Suggested patterns:

```text
CASE-001
MAT-BRG-001
CAND-A
REQ-001
TEST-001
APR-001
ACT-001
```

## Logging

Log:
- case ID;
- case version;
- tool;
- input hash if useful;
- output status;
- duration;
- error code.

Do not log secrets.

---

# 36. Suggested Environment Variables

`[IMPLEMENTATION]`

Do not hardcode secrets.

Example `.env.example`:

```bash
AWS_REGION=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=

BEDROCK_MODEL_ID=
BEDROCK_KB_ID=

S3_DOCUMENT_BUCKET=
S3_CASE_BUCKET=

AGENTCORE_RUNTIME_ID=
AGENTCORE_GATEWAY_ID=

APP_ENV=development
LOG_LEVEL=INFO

FRONTEND_API_URL=http://localhost:8000
BACKEND_PORT=8000
```

Adapt based on final stack and AWS credentials model.

---

# 37. Open Questions

Track unresolved architecture decisions here.

- [x] Local frontend uses plain HTML/CSS/JavaScript (ADR-007); future framework adoption requires a concrete reason.
- [x] Local HTTP backend uses the Python standard library (ADR-007); public deployment server remains undecided.
- [x] Local recovery-case persistence uses SQLite and lossless JSON aggregates (ADR-007); deployment storage remains undecided.
- [ ] Is DynamoDB enough for MVP or is relational storage preferable?
- [ ] What AWS Region is available?
- [ ] Which Bedrock model is permitted?
- [ ] Are AgentCore Runtime and Gateway available in the hackathon account?
- [ ] Will Knowledge Base ingest PDFs directly as expected?
- [x] Case hash uses SHA-256 over canonical JSON decision content plus case identity, version, and previous hash (ADR-006).
- [x] Any tracked source-version or decision-content change creates a new version; exact no-ops do not (ADR-006).
- [ ] Will scenario ranking be explicit weighted logic or non-ranked presentation?
- [ ] How realistic should supplier cost fixtures be?
- [ ] What user roles are needed in the UI?
- [ ] How will test calendars be represented?

Do not invent answers silently. Record the decision in ADRs when resolved.

---

# 38. Known Risks

## Risk 1 — Building the agent too early

Impact:
agent appears functional but core logic is unreliable.

Mitigation:
implement deterministic tools first.

---

## Risk 2 — Turning the system into a chatbot

Impact:
project loses its evidence-bound workflow differentiation.

Mitigation:
make recovery case, evidence matrix, dependency graph, and action gate first-class UI/state.

---

## Risk 3 — LLM performs arithmetic / safety logic

Impact:
non-reproducible decisions and weak judging credibility.

Mitigation:
keep calculations in deterministic services.

---

## Risk 4 — Overengineering AWS integration

Impact:
time lost on infra instead of end-to-end demo.

Mitigation:
prioritize canonical workflow; mock enterprise adapters where proposal allows.

---

## Risk 5 — UI hides the core innovation

Impact:
judges see “another manufacturing assistant.”

Mitigation:
visually emphasize:
- shortage deadline;
- arrival vs readiness;
- evidence gaps;
- qualification critical path;
- stale approval invalidation.

---

## Risk 6 — Unsupported novelty claims

Impact:
easy challenge from judges.

Mitigation:
use the proposal's focused contribution rather than “market first.”

---

# 39. AI Agent Operating Instructions

Any AI coding agent reading this file should follow these rules.

## Before coding

1. Read this entire file.
2. Inspect the existing repository.
3. Inspect recent commits.
4. Read current TODO/progress section.
5. Identify which phase is currently active.
6. Do not redesign architecture without a concrete reason.

## Before creating a new service/module

Ask internally:
- Does an existing module already own this responsibility?
- Is this deterministic or agentic?
- Does the canonical demo require it?
- Is it P0/P1/P2/P3?
- Does it preserve proposal boundaries?

## When uncertain

Prefer:
- explicit state;
- typed schemas;
- deterministic calculations;
- small tools;
- visible provenance;
- fail-closed behavior.

Avoid:
- magic hidden state;
- free-form JSON when typed schema is possible;
- LLM-generated arithmetic;
- autonomous write authority;
- unsupported assumptions;
- unnecessary agents.

## After meaningful work

Update:

```text
# 26. Current Progress Tracker
# 27. Session Progress Log
# 28. Architecture Decision Records
```

If an architecture decision changes, record:
- old decision;
- new decision;
- reason;
- consequences.

---

# 40. Suggested First Local Coding Session

`[IMPLEMENTATION]`

The first coding session should **not** involve Bedrock.

Goal:

> Make the core recovery scenario work deterministically using local JSON fixtures.

Recommended tasks:

```text
1. initialize repository
2. add project folder structure
3. add synthetic fixture schemas
4. create materials.json
5. create bom.json
6. create production_orders.json
7. create purchase_orders.json
8. implement getExposure()
9. write unit tests
10. print / return shortage date + exposed orders
```

Definition of done:

```text
Given a fixed stock level, known receipts, BOM consumption, and dated production orders,
the program produces a reproducible shortage date and affected-order list.
```

Only after this is correct should the implementation move to:
- recovery options;
- requirement comparison;
- qualification simulation;
- document retrieval;
- agents.

---

# 41. Minimal Local Scenario Fixture

`[IMPLEMENTATION — illustrative starting point]`

This is not official proposal data. It is a recommended fixture shape.

```yaml
material:
  id: BRG-001
  name: Assembly Bearing 25mm
  usable_stock: 300

demand:
  average_per_day: 100

original_supply:
  expected_delivery_day: 21

candidate_a:
  id: CAND-A
  eta_day: 2
  bore_mm: 25
  dynamic_load_kn: 16
  lubricant_temperature_evidence: null
  plant_release: false

candidate_b:
  id: CAND-B
  eta_day: 2
  bore_mm: 30
  dynamic_load_kn: 18
  plant_release: false

recovery:
  shortage_day: 3

qualification_candidate_a:
  temperature_test_days: 2
  engineering_review_days: 0.5
  quality_review_days: 0.5
```

Expected reasoning:

```text
Candidate B:
hard bore mismatch → reject

Candidate A:
delivery before depletion → yes
technical evidence complete → no
qualification complete before depletion → no
status → conditional / blocked pending qualification
```

---

# 42. README Relationship

This file is intentionally more detailed than `README.md`.

Recommended:

## README.md

Keep concise:
- what project does;
- how to run;
- architecture summary;
- links to docs.

## PROJECT_CONTEXT.md

Use as:
- AI-agent handoff;
- architecture memory;
- project decisions;
- progress tracker;
- scope guardrail.

README should link here:

```markdown
For architecture, business logic, current progress, and AI-agent handoff context,
see [PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md).
```

---

# 43. Source-of-Truth Hierarchy

If information conflicts, use this priority order:

```text
1. Latest explicit team decision
2. Submitted proposal
3. PROJECT_CONTEXT.md current ADRs
4. Implemented + tested behavior
5. AI-agent suggestion
```

An AI agent must not silently override levels 1–4.

If implementation intentionally deviates from proposal:
- document the deviation;
- explain why;
- assess whether demo/pitch language must change.

---

# 44. Final Project Mental Model

The shortest correct mental model is:

```text
A material disruption occurs.

The system first determines whether production is actually exposed.

It exhausts immediately usable approved recovery options.

If only unqualified candidates remain, it assembles application-specific evidence
and explicitly records what is known, mismatched, unknown, or blocked.

It then calculates whether the candidate can complete all required qualification
dependencies before the production recovery window closes.

The agent coordinates this investigation.

Deterministic services perform calculations and constraints.

Humans retain release authority.

Any approved action is tied to the exact case/evidence version reviewed.

If the evidence changes, stale authorization becomes invalid.
```

That is **Material Continuity**.

---

# 45. Immediate Next Action

Current recommended next step:

```text
OpenAI web review and the interactive read-only workflow viewer are implemented
and live-verified. Next implement controlled PDF upload, immutable revisions,
page-aware extraction, and ingestion-driven case re-investigation. Keep model
outputs separate from evidence and preserve deterministic/human gates.
```

Proposed implementation priorities:

```text
document upload/revision and actual extraction
→ ingestion-driven evidence review and source-version updates
→ full live evidence/retrieval/runtime adapters when access is verified
→ deployment-appropriate server/storage/identity
→ UI visual polish and full web acceptance verification
```

AWS remains the proposal's target architecture. The user has approved an interim
optional OpenAI inference adapter (ADR-008), not a wholesale cloud migration.
The supplied SAP manual describes additional organizer facilities, but SAP
account access was deferred. The local frontend/backend/database choices
are recorded in ADR-007; public deployment choices and sync cadence remain open.
`CHATGPT_HANDOFF_2026-10-13.md` is the planning snapshot from before this functional
web implementation. Use this tracker and latest session log for current progress.
