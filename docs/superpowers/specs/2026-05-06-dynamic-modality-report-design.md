# Dynamic Modality Report Design

## Goal

Make the protected health report respond to the selected data modalities. The report should keep the current clean dashboard style, but replace the fixed four-chart layout with visual health-theme sections that appear, sort, and summarize based on available modality evidence.

## Approved Direction

Use a hybrid report model:

- Health themes are the primary report structure.
- Selected modalities appear as evidence tags inside each section.
- Unsupported themes do not occupy large empty panels.
- Missing modality coverage is summarized in a compact `Missing signals` panel.
- The report favors charts and compact indicators over long narrative text.

The selected layout is `Section Story`: each health theme is rendered as a visual-first block with one main chart, a few compact metrics, one short insight, and modality source tags.

## Report Hierarchy

The report renders in this order:

1. `Integrated Summary`, always visible when report data exists.
2. `Missing signals`, visible when selected modalities cannot support one or more useful health themes.
3. Top 3 expanded health sections, selected by priority.
4. Remaining available sections as compact visual tiles.
5. Recommendations, rewritten as short scan-friendly bullets.

This controls report length when many modalities are selected while still keeping all available dimensions visible.

## Health Theme Pool

The backend should generate sections from this theme pool:

| Theme ID | Title | Supporting Modalities | Primary Visual |
| --- | --- | --- | --- |
| `mobility` | Mobility & Fall Stability | `imu`, `uwb`, `rgb`, `ntu` | stability gauge or gait/drift trend |
| `vitals` | Cardiorespiratory Vitals | `csi`, `uwb` | reference-band bar chart |
| `sleep` | Sleep & Recovery | `depth`, `csi` | recovery distribution or staged bars |
| `activity` | Activity Pattern | `imu`, `uwb`, `rgb`, `ntu` | donut or stacked bar |
| `medical_screening` | Medical Image Screening | `retina`, `chest`, `path`, `blood` | risk tile matrix |
| `integrated_risk` | Integrated Risk Summary | any 2 or more selected modalities | radar or confidence matrix |

Theme availability is based on selected modality IDs, not only on model results. A theme can include partial evidence when at least one supporting modality is selected.

## Section Data Shape

Extend `report` with a new section-oriented shape while preserving existing fields during migration.

```json
{
  "summary": {
    "title": "Integrated Summary",
    "health_index": 0.76,
    "overall": "Watch",
    "drivers": ["Reduced sleep efficiency", "Elevated BP proxy"],
    "coverage": {
      "selected_modalities": ["imu", "uwb", "csi", "depth"],
      "available_theme_count": 4,
      "total_theme_count": 6
    }
  },
  "missing_signals": [
    {
      "theme_id": "medical_screening",
      "title": "Medical Image Screening",
      "missing_modalities": ["retina", "chest", "path", "blood"],
      "message": "Add medical image modalities to unlock image screening views."
    }
  ],
  "sections": [
    {
      "id": "mobility",
      "title": "Mobility & Fall Stability",
      "status": "watch",
      "priority": 91,
      "expanded": true,
      "source_modalities": ["imu", "uwb"],
      "insight": "Movement variability is elevated relative to the current demo reference.",
      "chart_type": "stability",
      "chart": {
        "score": 0.68,
        "trend": [0.52, 0.58, 0.61, 0.68],
        "bands": [
          {"label": "Low", "min": 0.0, "max": 0.4},
          {"label": "Watch", "min": 0.4, "max": 0.7},
          {"label": "Stable", "min": 0.7, "max": 1.0}
        ]
      },
      "metrics": [
        {"name": "Cadence", "value": 92, "unit": "spm", "status": "normal", "ref": "90-130"},
        {"name": "Movement drift", "value": 0.07, "unit": "", "status": "watch", "ref": "<0.08"}
      ]
    }
  ],
  "compact_sections": []
}
```

Existing `metrics`, `charts`, `fall_risk`, `narrative`, and `recommendations` should remain until the frontend no longer depends on them.

## Priority Rules

Expanded sections are chosen by:

1. Higher abnormality or risk status.
2. Higher source modality coverage.
3. Stable theme order: `integrated_risk`, `mobility`, `vitals`, `sleep`, `activity`, `medical_screening`.

The frontend can trust `expanded: true` and does not need to re-sort unless the backend omits it.

## Visual Density

Use a chart-first but still interpretable layout:

- Main visual receives most of the section area.
- Each expanded section shows 2-4 metrics.
- Each section has one sentence of interpretation.
- Long paragraphs are avoided.
- Recommendations stay outside the status section and remain short bullets.

## Privacy Behavior

The structured dashboard report may keep precise backend values for local display, matching the current behavior. The external LLM prompt must continue using bucketed privacy summaries. If the LLM prompt includes section context, it should include section title, status bucket, source modality labels, and bucketed metric names, not precise scores.

## Compatibility

Frontend rendering should prefer `report.sections` when present. If absent, it should fall back to the current fixed report renderer so existing API responses still display.

Backend tests should assert both the new section shape and the old compatibility fields during migration.

