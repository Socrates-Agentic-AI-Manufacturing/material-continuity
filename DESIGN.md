---
name: Material Continuity
description: Functional review workspace
colors:
  ink: "#1b2b39"
  muted: "#485b6a"
  accent: "#075d78"
  line: "#c7d1d8"
  surface: "#fff"
  background: "#f2f5f7"
  danger: "#8d211d"
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

# Functional review workspace

## Overview

This records the initial working web surface, not a final visual identity.
The user explicitly deferred polish in favor of functioning workflows. Keep
Operate mode: reviewer-oriented navigation, tables, native forms, and readable
backend facts. The Agent Workflow extends this system with an interactive
explanation and replay viewer inspired by n8n; it is not a workflow editor.

Desktop browser flow was exercised through login, evidence, scenarios, approval,
mock task creation, and reload persistence. Optional OpenAI advisory is available
through an explicit paid review request. Documents & Data extends the same native
form and table language with local PDF upload, page-text inspection, optional paid
OpenAI extraction, human evidence review, and revision activation. Public deployment
remains unavailable; OCR and internet/AWS evidence sources remain unconnected.

## Colors

Use the existing teal accent for links, primary actions, and selected navigation;
light neutral surfaces, dark ink, muted supporting text, and thin line dividers
remain the base. Requirement states include text as well as color.

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
added between Summary & Options and Evidence Review. Wrap navigation naturally;
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

Keep flat surfaces with borders and tonal differences, without shadows. The
canvas dot grid and connector lines explain spatial relationships. A teal
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
