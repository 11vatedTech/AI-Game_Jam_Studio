# Video, Cinematography, Editing, and Motion Graphics

## Scope

Concept, treatment, script, shot list, storyboard, animatic, cinematography, camera, lighting, scene creation, motion capture, editing, compositing, color grading, motion graphics, captions/subtitles, sound mix, finishing, and platform-specific exports.

## Candidate ecosystem

Blender, Kdenlive, Natron, FFmpeg, OBS, OpenTimelineIO; optional DaVinci Resolve, Premiere Pro, After Effects and Nuke where they justify cost and license. Evaluate each application's automation API, batch/headless capability, project interchange and media management.

## Pipeline

Brief/treatment → script → shot breakdown → storyboard/animatic → assets/locations → capture/render → editorial assembly → sound design → color/compositing → subtitles/accessibility → QC → export/delivery.

## Acceptance

- Shot continuity, screen direction, composition, pacing, exposure, focus, camera movement and motivated transitions.
- Consistent color pipeline, correct frame rate, resolution, aspect ratio, pixel aspect, audio sync and timecode.
- No black frames, missing media, dropped-frame surprises, broken titles, clipping, unintended pops or subtitle timing defects.
- Correct codec/container/profile for destination; verify actual encoded file and metadata.
- Deliver timeline/project and referenced media when editable source is required.

## Interchange

OpenTimelineIO represents editorial structure and references media externally; it does not embed video or audio media. Map file paths and adapters deliberately; validate round trips rather than assuming every editor preserves all metadata.
