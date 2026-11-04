# Engineering QA and Application Verification

## General gates

- Static analysis, format/lint, type checking, unit tests, integration tests, build, runtime smoke, security scan, dependency/license audit, resource/performance profile, and documentation.
- For adapters, test invalid input, unsupported version, connection loss, app busy, timeout, cancellation, duplicate request, partial failure, crash/restart, concurrent access, permission denial, and corrupted project.
- For plugins, test install/upgrade/disable/uninstall, rollback and app-version compatibility.
- For pipelines, test missing source, partial output, repeated run, cache invalidation, and clean-room reproduction.

## Game-engine QA

Use engine-specific facilities: Unreal Automation/Functional tests, Unity Test Framework and build tests, Godot headless/runtime automation, plus black-box interaction tests. Verify editor state and packaged runtime separately. Capture application logs, crash output, performance profile and rendered frames.

## Visual regression

- Capture in controlled environment.
- Compare image regions and perceptual metrics.
- Exclude only known dynamic regions, documenting why.
- Require human review on changed golden images or where metric thresholds are ambiguous.
- Keep baselines versioned and trace them to approved releases.

## Runtime and performance

Measure frame-time percentiles, CPU/GPU time, memory/VRAM, load time, shader compilation, draw calls, triangles, overdraw, audio voices, network performance, and platform-specific limits. Use target hardware and representative worst-case scenes.

## Build reproducibility

Record toolchain, compiler, SDK, engine, plugins, dependencies, config, environment variables, build command and artifact hash. Test from clean checkout or staged source snapshot. Do not claim deterministic builds unless proven.
