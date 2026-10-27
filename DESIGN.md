---
name: Material Continuity
description: Functional review workspace
colors:
  ink: "#102536"
  muted: "#5d7180"
  accent: "#006d87"
  line: "#d7e0e5"
  surface: "#fff"
  background: "#eef2f4"
  danger: "#a12822"
typography:
  body:
    fontFamily: "system-ui, sans-serif"
    fontSize: "16px"
    lineHeight: 1.5
  headline:
    fontSize: "28px"
    lineHeight: 1.2
  title:
    fontSize: "21px"
  label:
    fontSize: "13px"
rounded:
  control: "4px"
  panel: "6px"
  workspace: "8px"
  node: "12px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "#fff"
    rounded: "{rounded.control}"
    padding: "8px 16px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.accent}"
    rounded: "{rounded.control}"
    padding: "8px 16px"
---

# Recovery decision workspace

## Overview

The workspace uses an enterprise recovery-control direction: Fiori-style object
headers and decision summaries, Carbon-style tables and semantic status tags,
and an inspectable n8n-inspired workflow canvas. The visual hierarchy helps a
reviewer move from exposure to evidence, scenarios, and human authorization
without changing the backend decision model. The Agent Workflow remains an
explanation and replay viewer, not a workflow editor.

Desktop browser flow was exercised through login, evidence, scenarios, approval,
mock task creation, and reload persistence. Optional OpenAI advisory is available
through an explicit paid review request. Documents & Data extends the same native
form and table language with local PDF upload, page-text inspection, optional paid
OpenAI extraction, human evidence review, and revision activation. Public deployment
remains unavailable; OCR and internet/AWS evidence sources remain unconnected.

## Colors

Use teal for navigation, links, and primary actions; dark slate for authority and
decision summaries; and light neutral layers for data-heavy surfaces. Semantic
amber, red, and green are reserved for critical, negative, and positive states.
Every state retains a concise text label so color is never the only signal.

Within the workflow viewer, violet identifies OpenAI advisory, amber marks human
gates, and green identifies mock QMS tasks. Preserve owner and status labels and
the legend so color is never the sole explanation of responsibility or outcome.

## Typography

Retain the system font stack. Body copy uses the body role; primary headings use
the headline role, reduced to (24px) on narrow screens. Section headings use the
title role; tables use (14px) with tabular numerals. Workflow node titles use
(15px), inspector body copy (14px), and supporting labels (12–13px). Keep full
results readable in the inspector rather than fitting them into node tiles.

## Layout

Keep the centered content container (1280px maximum) with (28px) desktop gutters
and (16px) gutters at widths of (700px) or less. Main navigation remains Overview,
Recovery Cases, and Documents & Data. Case links/tabs retain Summary & Options,
Evidence Review, Recovery Scenarios, and Approval & Actions, with Agent Workflow
added between Summary & Options and Evidence Review. Overview uses KPI cards and
a priority table. Case pages use an object header, release banner, sticky section
navigation, and a decision brief before detailed tables. Documents keeps uploads
inside a disclosure so the corpus remains the default focus. Scroll navigation;
keep accessible table headers/captions and horizontal table scrolling on narrow
screens. Document revision and corpus tables scroll within their own containers;
long source text and proposal quotes wrap without widening the page. Keep PDF
upload/review forms within the established (500px) form width. Page-text disclosures
use internally scrolling, wrapped text with a (360px) maximum height.

The workflow workspace pairs the connected-node canvas with a readable inspector
on the right (290px, reduced to 250px at 1000px or less). At (700px) or less, stack the
inspector beneath the board and initialize the list view. Keep the alternative
canvas available. List replay scrolls only its internal list to reveal the
selected node; it must not move the document away from replay controls.

## Elevation & Depth

Use subtle, low-contrast shadows only to separate actionable cards and data
surfaces from the workspace background; hierarchy still relies primarily on
borders and tonal differences. The canvas dot grid and connector lines explain spatial relationships. A teal
selection outline identifies the inspected node; the visible keyboard focus
outline remains distinct.

## Shapes

Use the established small control corners, gently rounded panels, and slightly
larger workflow workspace and node corners from the frontmatter. Nodes are
compact connected tiles, while forms and tables retain their native structure.

## Components

- Buttons and forms: keep labelled native controls, visible focus, (44px)
  minimum button/text-field/select height, disabled states, and live error/success messages.
  The paid review form requires an unchecked cost-consent checkbox and an explicit
  submit action. Show provider availability, progress, and errors beside it;
  stale sources or unavailable configuration disable the request. No automatic
  request or retry is triggered by opening the page, switching views, or replay.
- PDF upload and source inspection: use labelled native candidate, stable document
  ID, revision, and file fields, followed by an explicit upload action. Show file
  limits and process status in text. Preserve the form on upload rejection, clear
  pending status, and restore eligible controls. Native disclosures expose the
  original page text; keep the original PDF link visible beside revision identity.
- Evidence proposals: show each property/value with its applicability, quoted
  source text, and a direct PDF page link. Acceptance checkboxes begin unchecked;
  unavailable claims remain disabled and UNKNOWN. A separate unchecked scope
  confirmation precedes saving. Persisted reviewer identity and disabled selection
  distinguish an immutable saved review from an editable proposal. The PDF
  extraction form has its own unchecked paid OpenAI consent and explicit submit.
- Revision authority: label active and archived/unactivated revisions in text in
  the revision table. Place the invalidation warning and unchecked confirmation
  beside activation. Explain that activation immediately blocks old approvals and
  actions, while case results require a manual reinvestigation to refresh. Keep
  this authority language adjacent to the action rather than relying on color.
- Workflow nodes: use a button with owner/icon, sequence, title, target, and
  textual status. Selection uses `aria-pressed` and updates the adjacent inspector.
  Connected nodes support inspection only; do not imply editable execution rules.
- Workflow source selector: distinguish the grouped local case map from the
  actual recorded OpenAI tool order. Keep persisted AI review snapshots separate
  from local investigation records; label a saved review from an old case version
  or source state as an archive. Never present it as current evidence.
- Canvas and replay: expose canvas/list switching, fit, zoom, pointer pan, keyboard
  pan, and previous/play-pause/next controls. Replay selects existing records only;
  it cannot execute tools or consume API credits. Stop replay on view changes and
  navigation. Disable canvas-only controls in list mode.
- Inspector: show the selected node's explanation and readable result summary
  before native expandable snapshot-context and full-output JSON sections. Wrap
  long output and allow internal scrolling. Retain links into Approval & Actions
  for the human gate and task receipt nodes.
- Status and authority: approval, source freshness, and action eligibility come
  from server responses. UI formatting must not reimplement domain comparisons
  or approve locally. Advisory, feasible scenarios, qualification plans, and mock
  task receipts never indicate production release authority.

## Do's and Don'ts

- Do preserve the established navigation, tables, native forms, focus behavior,
  accessible semantics, and functionality-first scope when extending the viewer.
- Do distinguish prepared evidence, locally read PDF text, unverified extraction
  proposals, human-reviewed claims, and active/archive revisions in visible copy.
- Do keep backend facts separate from advisory prose and preserve explicit human
  consent, evidence acceptance, and activation controls.
- Don't introduce a new visual identity or require imagery/decorative animation
  for this milestone; visual-world selection and comprehensive polish remain deferred.
- Don't turn replay into execution, invent missing evidence, or infer authorization
  from node color, connector order, AI output, or a qualification task.
