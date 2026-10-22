# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Purpose and users

Material Continuity supports manufacturing recovery review by Planning,
Engineering, and Quality when a purchased assembly bearing is delayed or held.
The case ties production exposure to applicable technical evidence,
qualification timing, recovery scenarios, human approvals, and action receipts.
See PROJECT_CONTEXT.md for the primary product and architecture authority.

## Current implementation choice

Functional-first local web MVP: Python standard-library HTTP adapter, SQLite
case/session persistence, and plain HTML/CSS/JavaScript. Existing deterministic
core and local agent workflows remain owners of business decisions. No new
third-party runtime dependency. Public hosting is not supported by this local
HTTP demo; production deployment/auth/provider choices remain open.

## Confirmed constraints

- The user explicitly prioritizes working functionality; visual polish comes later.
- Three main navigation entries: Overview, Recovery Cases, Documents & Data.
- Case detail groups Summary/Options, Agent Workflow, Evidence Review, Scenarios, Approval/Actions.
- Evidence gaps remain UNKNOWN; hard mismatches reject; production release needs humans.
- Operational data is synthetic and QMS writes are mock. Explicit optional OpenAI review is live-verified. Uploaded candidate PDFs are parsed per page; OpenAI evidence proposals require reviewer acceptance and explicit active-revision selection before deterministic comparison. No OCR, supplier internet retrieval or AWS deployment.
- The user requested an n8n-like interactive workflow viewer: node inspection and replay, not editing executable workflow or authorization rules.
- Distinguish the grouped local case map from the actual recorded OpenAI tool order. Replay never invokes tools or consumes API credits.
- Approval identity and role come from server sessions; domain calculations stay on the server.

## Content and verification

Use the synthetic fixtures and twelve PDFs in data/documents. The scenario dates
are fixed in September/October 2026, not current live factory data. No currency
symbol is implied by integer-cent cost fixtures. Demonstrate behavior with real
backend responses, readable evidence citations, and explicit blocked reasons.
