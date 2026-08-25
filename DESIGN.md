---
name: Federal Civil Portfolio Intelligence
description: Governed enterprise analytics cockpit for full-population federal civil operations evidence.
colors:
  ink: "#182230"
  muted: "#667085"
  subtle: "#8a94a3"
  navigation: "#0c1728"
  navigation-raised: "#142238"
  surface: "#ffffff"
  canvas: "#f5f7f8"
  line: "#d6dce2"
  soft-line: "#e8ecef"
  operational-teal: "#167f85"
  operational-teal-dark: "#0e676d"
  operational-teal-soft: "#e5f3f2"
  caution-amber: "#b8741a"
  caution-amber-soft: "#fff3dc"
  error-red: "#b54740"
  focus-blue: "#2e90fa"
typography:
  display:
    fontFamily: "IBM Plex Sans, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "clamp(27px, 3vw, 38px)"
    fontWeight: 700
    lineHeight: 1.08
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "IBM Plex Sans, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "17px"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "normal"
  title:
    fontFamily: "IBM Plex Sans, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "15px"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  body:
    fontFamily: "IBM Plex Sans, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  label:
    fontFamily: "IBM Plex Sans, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "9px"
    fontWeight: 750
    lineHeight: 1.35
    letterSpacing: "0.05em"
rounded:
  square: "0px"
  control: "4px"
  status: "999px"
spacing:
  tight: "4px"
  compact: "8px"
  control: "12px"
  panel: "18px"
  section: "24px"
components:
  button-primary:
    backgroundColor: "{colors.operational-teal-dark}"
    textColor: "{colors.surface}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
    height: "36px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
    height: "36px"
  field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "7px 9px"
    height: "36px"
  navigation-active:
    backgroundColor: "{colors.navigation-raised}"
    textColor: "{colors.surface}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "11px 12px"
  analysis-panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.square}"
    padding: "18px"
---

# Design System: Federal Civil Portfolio Intelligence

## Overview

**Creative North Star: "The Governed Portfolio Cockpit"**

The interface is a dense, calm operational workspace for users who need an executive read and immediate analytical depth. A navy shell establishes institutional authority, white analytical surfaces keep evidence legible, and compact controls preserve room for high-density tables and charts. The system feels precise, sober, and continuously auditable.

Hierarchy comes from placement, tonal contrast, rules, and typographic weight rather than decoration. Global scope remains visually attached to the evidence it controls. Support, method, source period, and limitations stay near the values they qualify. Product boundaries remain in the collapsed Methods disclosure instead of competing with the analytical summary.

**Key Characteristics:**

- Dense governed analytics with a clear 30-second summary layer.
- Persistent navy operational shell and white evidence surfaces.
- Restrained teal for active states, amber for caution, and red only for blocking errors.
- Compact squared controls, structured dividers, tabular numerals, and plain operational language.
- One global scope that visibly binds metrics, charts, rankings, cohort context, and export.
- Responsive disclosure through explicit More and Filters controls.

## Colors

The palette is institutional and low-saturation. Navy and neutral surfaces carry the interface; semantic color is scarce and always meaningful.

### Primary

- **Operational Teal:** Use for active navigation markers, selected rows, chart emphasis, links, primary actions, and available states.
- **Deep Operational Teal:** Use when teal must support white text or stronger interactive emphasis.
- **Soft Operational Teal:** Use for selected or available backgrounds without obscuring dense text and numbers.

### Secondary

- **Caution Amber:** Use for aging pressure, withheld intersections, and bounded caution. It never means failure.
- **Error Red:** Use only for blocking errors and failed requests. It never decorates ordinary negative movement.
- **Focus Blue:** Reserve for visible keyboard focus so focus remains distinct from data state and selection.

### Neutral

- **Navigation Navy:** The persistent operational shell and compact mobile navigation surface.
- **Raised Navigation Navy:** Active navigation and elevated dark controls.
- **Ink:** Primary text and numerical values.
- **Muted and Subtle:** Supporting copy, metadata, timestamps, and low-priority qualifiers.
- **Surface and Canvas:** White analytical planes over a cool gray application field.
- **Line and Soft Line:** Structural boundaries, table rules, dividers, and quiet subdivisions.

### Named Rules

**The Semantic Scarcity Rule.** Teal, amber, and red appear only when they communicate selection, caution, or failure. Neutral structure carries everything else.

**The Evidence Class Rule.** Observed evidence and synthetic scenarios always carry explicit wording and distinct semantic treatment.

## Typography

**Display Font:** IBM Plex Sans with the system sans-serif stack.

**Body Font:** IBM Plex Sans with the system sans-serif stack.

**Character:** One disciplined grotesk family carries the whole product. Tight headings feel decisive; compact body and label sizes support dense scanning; tabular numerals keep columns and metric strips stable.

### Hierarchy

- **Display** (700, `clamp(27px, 3vw, 38px)`, 1.08): Workspace titles only. Keep the wording factual and short.
- **Headline** (700, 17px, 1.25): Major evidence and workflow sections.
- **Title** (700, 15px, 1.3): Analytical panel headings and compact card titles.
- **Body** (400, 13px, 1.55): Explanations and guidance, generally capped near 75 characters per line.
- **Label** (750, 9px, 0.05em tracking): Uppercase field labels, metric labels, state badges, and table headers.
- **Data** (600 to 750): Numerical values use tabular figures; large metrics may scale from 22px to 31px.

### Named Rules

**The Operational Hierarchy Rule.** Large type names the workspace, not the result. Evidence earns emphasis through stable alignment, tabular figures, and proximity to its qualifiers.

## Layout

The desktop application uses a fixed operational rail and a fluid analytical workspace. The rail is 232px wide at full desktop width and contracts to 190px below 1180px. The evidence workspace is centered with a maximum width of 1540px and uses a dense 18px to 24px panel rhythm. The sticky workspace bar is 58px high, and the global query bar remains directly below it so scope never detaches from results.

The primary dashboard follows a deliberate sequence: title and snapshot, global scope, metric strip, scope interpretation, analytical grid, and methodology. The analytical grid favors a wider trend column and a narrower comparison column. Panels join through shared 1px rules rather than isolated floating cards. Tables use 8px by 9px cells, right-align numerical columns, and preserve horizontal scrolling when width is constrained.

Below 1180px, the analytical grid becomes a single column and scenario inputs stack above outputs. At 760px and below, the side rail becomes a sticky top navigation; secondary destinations move into an explicit More disclosure. The global scope collapses behind an explicit Filters control. Metric strips become two columns, methodology becomes one column, and scenario summaries stack. Never hide scope or secondary destinations without a named disclosure control.

**The Bound Scope Rule.** Filters, scope interpretation, result panels, and export represent one shared analytical state. A scope change must visibly rebind the entire workspace.

## Elevation & Depth

The system is flat by default. Depth comes from the navy shell, white analytical planes, cool canvas, and structural 1px rules. Shadows are reserved for persistent controls that cross content layers: the sticky global query bar uses a restrained shadow (`0 6px 16px rgba(12, 23, 40, .12)`), and the mobile More menu uses a stronger directional shadow (`0 14px 28px rgba(5, 13, 24, .32)`). Cards and analytical panels do not float at rest.

### Shadow Vocabulary

- **Sticky Control:** A low, compact shadow that separates a persistent scope control from scrolling evidence.
- **Disclosure Menu:** A stronger shadow used only when a temporary menu overlays the workspace.

### Named Rules

**The Structural Depth Rule.** Use tonal layers and borders for ordinary hierarchy. Add a shadow only when an element is sticky or temporarily overlays another layer.

## Shapes

The form language is squared and compact. Analytical panels, metric strips, tables, and scope summaries use square corners. Interactive controls use a restrained 4px radius for reliable recognition without softening the enterprise character. Fully rounded geometry is reserved for small state badges and circular status dots.

Borders are functional: 1px rules establish grids and containment, while a 2px inset teal marker identifies active navigation. Charts remain geometrically quiet, with thin axes, small data points, and limited smoothing.

**The Radius Allocation Rule.** Square corners belong to evidence surfaces, 4px corners belong to controls, and pill geometry belongs only to compact statuses.

## Components

### Navigation

The navigation is a dark operational index, not a decorative brand panel. Desktop items use left-aligned 13px labels with optional 10px descriptions. Active items use the raised navy surface and a 2px teal inset marker. On mobile, primary destinations share the top row, the active marker moves to the bottom edge, and secondary destinations open from More.

### Global Scope Bar

The global scope bar is the visual contract between user intent and analytical output. It uses a raised navy surface, compact uppercase labels, 36px dark fields, a fixed filing-period declaration, and adjacent Clear and Filters actions. Desktop scope remains sticky; mobile scope is collapsed by default and expanded explicitly.

### Buttons

- **Shape:** Compact rectangular controls with a restrained 4px radius and 36px minimum height.
- **Primary:** Deep teal with white text, used for the single committed action in a local workflow.
- **Secondary:** White with a neutral border and dark text; the dark-shell variant becomes transparent with a lighter border.
- **Text Action:** Underlined teal text for low-emphasis navigation between connected workspaces.
- **Hover / Focus / Disabled:** Hover deepens or lightly fills the existing treatment. All keyboard focus uses a 3px focus-blue outline with 3px offset. Disabled controls retain their geometry and reduce opacity.

### Fields

Inputs and selects are 36px high with a 1px border, 4px radius, 7px by 9px internal padding, and 12px text. Fields on white surfaces use ink on white; fields in the global scope bar use light text on raised navy. Labels remain uppercase and compact. Error copy uses error red and appears adjacent to the affected workflow.

### Segmented Controls

Segmented controls are one compact bordered unit with 30px minimum-height options. The selected option uses a desaturated slate-blue fill and white text. Segments divide with 1px rules and never become detached pills.

### Metric Strips and Analytical Panels

Metric strips are joined white cells with square corners and shared dividers. Each cell contains an uppercase label, a large tabular value, and a concise qualifier. Analytical panels use 18px padding, square containment, compact titles, nearby support metadata, and a chart, table, or explicit empty state. At mobile widths, panels separate with 12px gaps but keep their square white surfaces.

### Tables and Rank Links

Tables are compact, numerical, and horizontally scrollable. Headers use uppercase 9px labels on the cool canvas tone. Numbers align right; rank and identity columns align left. Interactive rank labels are visibly underlined, and selection uses the soft teal surface across the full row.

### Bounded States

Withheld intersections use an amber bordered field with the publication threshold and a plain explanation. Loading uses neutral skeleton blocks; fatal errors lead with error red, a factual title, a recovery explanation, and a retry action.

### Charts

Charts use teal for the main analytical series, amber for the oldest aging band, and slate blue for observed benchmark bars. Axes and split lines stay neutral. Tooltips use navy with white text. Animation is brief at 360ms with cubic-out easing and becomes effectively instantaneous when reduced motion is requested. Every chart requires a concise text summary through its accessible name.

### Methodology Disclosure

Methods, provenance, support, and publication rules live in a native disclosure below the evidence panels. The closed summary shows the release contract; the open state uses divided white columns and compact definition lists. This disclosure is secondary in hierarchy but never absent.

## Do's and Don'ts

### Do:

- **Do** keep one visible global scope attached to every governed analytical output.
- **Do** use square joined panels and 1px rules to support dense comparison.
- **Do** place source period, support, method, and limitation beside the value or view they qualify.
- **Do** use tabular numerals, compact labels, explicit empty states, and text summaries for charts.
- **Do** preserve keyboard focus, reduced motion, responsive More and Filters disclosures, and horizontal table access.
- **Do** label synthetic scenarios, observed historical context, and suppressed cells in words.

### Don't:

- **Don't** use semantic color as decoration or allow color alone to communicate status.
- **Don't** turn evidence panels into floating rounded cards or add shadows to ordinary surfaces.
- **Don't** introduce a marketing hero, oversized display type, decorative illustration, or courtroom imagery into the operational workspace.
- **Don't** hide filters, methodology, provenance, or limitations to make the dashboard appear simpler.
- **Don't** imply a forecast, estimate, or pending result when the product provides historical aggregate evidence.
- **Don't** mix synthetic planning amounts with observed metrics without a labeled visual boundary.
