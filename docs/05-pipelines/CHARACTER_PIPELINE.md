# Professional Character Pipeline

## Deliverables

Reference board, character brief, style/turnaround sheet, native source model, topology/UVs, material/texture set, rig, skin weights, animation set, export files, engine import configuration, runtime prefab/blueprint/scene, and visual/functional evidence.

## Pipeline stages and exit criteria

1. **Brief and silhouette:** role, personality, gameplay role, proportions, silhouette, animation needs, equipment, materials, target screen size and style. Pass when design reads at intended camera distance.
2. **Concept and turnaround:** front/side/back or sufficient orthographic references; key expressions/poses; proportion and design consistency.
3. **Primary model/sculpt:** correct proportions and form; no visual shortcuts; reference comparison.
4. **Retopology:** clean deformation loops; appropriate density; no unsupported topology tricks.
5. **UV and bake:** proper island layout, texel density, padding, tangent basis, cage settings; inspect bake artifacts.
6. **Materials/textures:** approved palette, physically/stylized appropriate response; channel and color-space verification.
7. **Rig and skin:** hierarchy, bind pose, joint orientation, weights, deformation test suite.
8. **Animation:** required states, transitions, contacts, loop checks, retargeting and motion capture cleanup if applicable.
9. **Export/import:** skeleton and animation mapping, scale, axis, materials, root motion, collision/sockets.
10. **Runtime:** integrate into controller/state machine; test movement, attacks, hit reaction, locomotion, camera, lighting and performance.
11. **Final review:** turntable, close-up, wireframe, texture sheet, deformation poses, animation contact sheet, engine runtime capture, logs and manifest.

## Mandatory test poses

Neutral bind pose; full arm raise; shoulder cross; elbow/wrist extremes; hip flexion; deep crouch; leg lift; wide stance; twist; facial extremes if applicable; equipment interaction; representative combat/locomotion states. The exact tests are rig-specific.

## Failure examples

Wrong silhouette; broken anatomy; poor topology; UV distortion; texture seams; skinning collapse; foot sliding; root motion drift; material mismatch; missing animations on import; visible clipping; bad in-game scale; or performance outside budget. Any P0/P1 failure blocks approval.
