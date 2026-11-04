# First End-to-End Game Vertical Slice

The initial vertical slice is the first proof that the studio is a production system, not an integration catalog. Select one engine from actual workstation inspection and toolchain compatibility. Do not add all engines before one end-to-end workflow works.

## Required outcome

A small complete, art-directed, playable experience with a title/menu path, one representative gameplay loop/level, coherent custom visual assets, animation, audio, UI, win/fail or completion condition, pause/settings where relevant, packaged build, performance data, and evidence. Scope is intentionally small enough for complete QA but deep enough to expose cross-discipline integration failures.

## Workflow

Brief → design pillars/core loop → art bible → level layout → player/enemy/prop concepts → production assets → rig/animation/materials → gameplay systems → UI/audio/VFX → integration → runtime playtest → repair → QA/regression → release package.

## Minimum production quality

- No final placeholder geometry/art, generic unreviewed AI image, default font, debug UI, or empty placeholder logic.
- Every asset is editable at the agreed production level and has a provenance record.
- Core loop works from fresh launch to completion/failure state.
- Controls, camera, animation, VFX, audio and UI provide coherent feedback.
- Automated tests cover critical gameplay state and input; manual playtest covers feel/readability.
- Runtime screenshots/video are captured from the packaged build, not only the editor viewport.
- Package opens/runs from a clean folder and passes smoke test.

## Acceptance checklist

- [ ] Fresh project setup is reproducible.
- [ ] Source, generated assets, imports and build dependencies are present.
- [ ] Art direction and reference board approved.
- [ ] All custom assets pass their discipline gates.
- [ ] Scene/level opens without critical import errors.
- [ ] Game launches and core loop works.
- [ ] Input, collision, animation, VFX, sound, UI and progression tested.
- [ ] Save/load and pause/resume tested where required.
- [ ] Performance meets declared budget.
- [ ] Build passes clean-room launch.
- [ ] Evidence package and known-limitations report complete.
