# Emberkeep Asset Pipeline — Recipe v1

**Status:** EXECUTED (this is the path that manufactured the reference production).
**Pinned toolchain:** ComfyUI v0.34.0, `flux-2-klein-4b-fp8` + `hunyuan_3d_v2.1`,
Blender 5.2.0 LTS, Godot 4.7.2.stable. Model weights are local and are not
redistributed; validate each model license before commercial use.

## Stages

1. **Prompt** — 2D concept with `workflows/generation/flux2_klein_txt2img.api.json`
   via `scripts/pipelines/comfy_exec.py` (substitute `__PROMPT__`, `__WIDTH__`,
   `__HEIGHT__`, `__SEED__`, `__STEPS__`, `__CFG__`, `__PREFIX__`). Validate the
   graph first with `comfyui.validate_workflow`; interrupt safely with
   `comfyui.interrupt`, never by killing the server.
2. **Lift** — image-to-mesh with `workflows/generation/hunyuan3d_image_to_mesh.api.json`,
   same runner. Record the workflow SHA-256 from the runner manifest.
3. **Author** — Blender native source under `source/assets/<name>/`:
   `author_assets.py`-class tooling plus `scripts/blender/asset_ingest.py`,
   emitting `<name>.blend` (editable truth), `<name>.glb` (engine interchange)
   and `<name>.ingest.json` (triangle counts, dimensions, lineage).
4. **Read back** — `blender.inspect_scene` on the `.blend` (native object,
   mesh, material and image inventory) before the asset leaves Blender.
5. **Integrate** — import into `Games/emberkeep/game` (Godot re-imports the GLB);
   verify with `godot.validate_project` and `godot.inspect_scene`.
6. **Prove** — headless editor import, deterministic `--smoke` slice, art-direction
   contract, critic thresholds, packaged export and clean-location launch
   (`reports/evidence/productions/emberkeep/03-package/PACKAGE_REPORT.json`).

## Reuse contract

A new asset repeats stages 1–6 with its own brief, seed set and ingest JSON.
Skipping read-back (4) or the packaged proof (6) downgrades the output to
unverified generation, not a pipeline product. Craft and rights review stay
human-gated; the critic triages, it does not certify.
