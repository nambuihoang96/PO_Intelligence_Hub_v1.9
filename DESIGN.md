---
name: PO Intelligence Hub
description: Dark research workspace with answers and inspectable evidence
colors:
  primary: "#416bd1"
  focus: "#7ea6ff"
  background: "#0c1119"
  panel: "#131d2a"
  raised: "#1b293b"
  border: "#32435a"
  foreground: "#edf3fc"
  muted: "#b3c2d7"
  success: "#83d9b6"
  error: "#ffabab"
  warning: "#f0cf90"
typography:
  headline:
    fontFamily: "Segoe UI, Arial, sans-serif"
    fontSize: "1.85rem"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Segoe UI, Arial, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.4
  body:
    fontFamily: "Segoe UI, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
rounded:
  control: "7px"
  answer: "12px"
spacing:
  compact: "8px"
  related: "12px"
  section: "28px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    rounded: "{rounded.control}"
    padding: "9px 14px"
---
# Design System: PO Intelligence Hub

## Overview

The approved visual direction is a professional dark dashboard for frequent research tasks. The question and its answer lead; internal workflow details stay within progressive disclosure. This document records the built v1.9 workspace, not the legacy Market/Studio styles.

## Colors

Primary blue marks the principal action and current state. Dark neutral surfaces separate navigation, input and answer content. Success, warning and error colors always accompany text describing the state.

**The Evidence Rule.** An attractive status treatment never substitutes for the underlying source or uncertainty.

## Typography

One system sans family carries controls, prose and data. Body prose is limited to 75 characters per line. Tables use tabular numerals; monospace is reserved for raw JSON and identifiers. Long questions wrap independently of short display names.

## Layout

Desktop uses a 260px navigation column and a flexible workspace; navigation reduces to 210px below 950px. Below 650px it stacks above the content, with a horizontally scrollable navigation row. Tables scroll inside their own container. Sections use 28px vertical padding; related controls use 12px gaps.

## Elevation & Depth

Tonal layers and thin borders establish hierarchy. The workspace uses no decorative shadows or entrance animations.

## Shapes

Controls have modest rounded corners. Answer and question containers have larger corners; small tags identify scope and are not action buttons.

## Components

Buttons have visible hover, active, disabled and keyboard focus states. Focus uses a three-pixel outline with a three-pixel offset. Primary buttons use semibold text. Form labels remain visible; errors use text near the affected input. Progress appears within the result rather than in a blocking overlay. Tables keep filters in their column headers.

## Do's and Don'ts

- Do show the answer, scope and evidence together.
- Do preserve input after validation errors.
- Do respect reduced motion and native keyboard behavior.
- Don't introduce decorative charts or statistics that imply unsupported market conclusions.

## v1.9.1 dashboard extension

The Overview uses a twelve-column grid: a primary chart spans eight columns and attention spans four; comparison tables span the full row. Below 1150px these stack. Below 650px operational KPIs form two columns. Bar comparisons require explicit periods; daily lines require at least four actual dates and do not bridge missing days. The source drawer preserves its run/evidence URL through reload. Blue controls indicate actions, not confidence. Coverage, legacy and stale (>7-day-old period end) labels accompany research context.
