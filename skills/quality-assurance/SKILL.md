# Skill: Production Quality Assurance

## Mission
Determine whether a deliverable satisfies its requirements in the real target application/runtime. Do not confuse tool success with product success.

## Procedure
1. Convert every requirement into a deterministic or explicitly reviewed acceptance criterion.
2. Run schema/file checks, native application read-back, integration/runtime tests, performance/security/compatibility checks as appropriate.
3. Validate artifacts by hash and metadata; verify all provenance/license fields.
4. Capture fixed-condition screenshot/render/video/audio and runtime logs.
5. Review craft with criterion-level rubric and linked evidence.
6. Triage defect severity; identify root cause; return defects to their correct upstream stage.
7. Re-run targeted and regression tests.
8. Issue PASS/FAIL/NOT_RUN/BLOCKED/WAIVED_WITH_APPROVAL per criterion. Never convert missing evidence into PASS.

## Release policy
No certification with any failed or NOT_RUN mandatory test, unresolved P0/P1, missing license/provenance, or unverified target runtime.
