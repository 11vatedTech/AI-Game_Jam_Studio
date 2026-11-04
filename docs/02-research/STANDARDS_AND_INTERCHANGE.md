# Standards, Interchange, and Long-Lived Project Data

Professional interchange formats are strategic infrastructure. The studio should preserve native editable sources while using stable standards to connect tools. A format is chosen by task, not by ideology; lossy conversions must be declared and tested.

| Standard/format | Intended use | Design requirements |
|---|---|---|
| OpenUSD | Layered scene composition, large 3D scene interchange, references/variants | Track schema/version, resolver/assets, units, coordinate systems, and application feature parity |
| glTF 2.x | Runtime delivery of 3D scenes/assets | Validate extensions, compression, materials, animation, and target engine behavior |
| FBX | Widely used DCC/engine compatibility | Treat as a compatibility bridge; test skeleton, animation, transforms, materials, and unit preservation |
| MaterialX | Material/shader graph interchange | Verify renderer/shader subset and color pipeline; do not assume identical renders across applications |
| OpenPBR | Standardized material model | Test conversion/mapping in each participating renderer |
| OpenColorIO / ACES | Color management and interchange | Pin configs, working/display spaces, OCIO version, and output transforms |
| OpenTimelineIO | Editorial timeline interchange | Stores editorial cut structure and media references, not the audio/video media itself; ensure media path mapping |
| WAV/BWF, FLAC, OGG, Opus, MIDI | Audio source, interchange, and runtime delivery | Declare sample rate, bit depth, channel layout, loudness, codec, loop points, markers, and licensing |
| SVG/PDF/PNG/TIFF/PSD/KRA/XCF | 2D graphics and print/image interchange | Preserve layered master when required; track profiles, transparency, DPI, bleed, and color space |
| STEP/IGES/STL/3MF | CAD/fabrication interchange | Verify units, geometry validity, tolerances, tessellation, and feature history loss |
| JSON/YAML/TOML + JSON Schema | Configuration and metadata | Version schemas; validate on read/write; reject unsafe implicit typing and unknown mandatory fields |
| OpenAPI / AsyncAPI | HTTP and event contract documentation | Generate/validate clients and conformance tests; version breaking changes |
| Git / LFS / DVC / content-addressed stores | Source and large-artifact lineage | Separate source code, large binaries, generated outputs, and datasets |

## Interchange principles

- Retain original native project and exporter version.
- Record transformation chain, settings, and validation results.
- Round-trip test the formats that claim editability.
- Use stable IDs for assets across app-specific paths.
- Keep color management and unit/axis conversion explicit.
- Include dependencies and relative references in delivery packages.
- Do not force every artifact into one universal format; use domain standards and adapters.
