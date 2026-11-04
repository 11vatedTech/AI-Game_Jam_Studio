# Example Evidence Package — Illustrative Structure

```text
release-evidence/
  release-report.md
  acceptance-matrix.csv
  environment/
    workstation-inventory.json
    app-versions.json
  plan/
    brief.md
    art-bible.md
    production-graph.json
  artifacts/
    manifest.json
    checksums.sha256
  tests/
    unit-results.xml
    integration-results.json
    runtime-smoke.json
    performance.json
  visual/
    hero-view.png
    context-capture.png
    contact-sheet.png
    review-report.json
  audio/
    loudness-report.json
    playback-review.md
  logs/
    application.log
    adapter.log
    workflow-trace.json
  provenance/
    third-party-bom.json
    license-review.md
```

Evidence file names and test formats may vary. The package must be traceable to the precise artifacts and tool versions that were released.
