# Evidence and Release Report Contract

## Evidence types

- Command transcript with exit status and environment.
- Test result files and machine-readable reports.
- Screenshots, viewport captures, turntables, contact sheets and video.
- Audio render/session/meters and playback review.
- Engine/editor logs, import logs, profiler captures and runtime traces.
- Build/package metadata and clean-room launch evidence.
- Artifact hashes, manifests, lineage, license notices and approvals.
- Human review notes and defect closure records.

## Evidence rules

Evidence must be attributable to the exact artifact version and test run. A screenshot from an earlier output cannot certify a modified artifact. Evidence is immutable once referenced by a release; corrections create new records.

## Release report sections

1. Release identity, version, date, scope and support matrix.
2. Delivered artifact list and hashes.
3. Requirements/acceptance matrix.
4. Test suite versions, result summary, full evidence links.
5. Visual/audio review status and representative captures.
6. Performance/resource results.
7. Security, dependency, license and provenance status.
8. Known issues, unsupported environments and untested requirements.
9. Reproduction/build/install instructions.
10. Approval and release decision.

## Release verdict

`PASS`, `PASS_WITH_APPROVED_LIMITATIONS`, `FAIL`, `BLOCKED`. Do not use “complete” where mandatory criteria are not passed. A release with approved limitations must disclose them prominently.
