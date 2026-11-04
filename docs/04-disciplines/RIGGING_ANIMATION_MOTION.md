# Rigging, Animation, Mocap, and Motion Design

## Coverage

Character/creature rigs; skeletal hierarchy; skinning; blend shapes/morph targets; facial rigs; control rigs; retargeting; keyframe animation; mocap cleanup; procedural motion; camera motion; motion graphics; cloth/hair secondary motion; root motion; animation state machines; and runtime integration.

## Candidate tools and interfaces

Blender Python API, Unreal Control Rig/Sequencer/animation tools, Unity animation systems, Godot AnimationTree/AnimationPlayer, and optional Maya/MotionBuilder/Houdini ecosystems. Evaluate AI-assisted motion/mocap products separately for rights, temporal quality and editability.

## Character rig acceptance

- Stable named hierarchy and required deform/non-deform controls.
- Correct joint orientation, bind pose, scale, and transform conventions.
- Skin weights deform cleanly across extreme poses; no severe candy-wrapper collapse or volume loss.
- Joint limits/control behavior are documented.
- Export skeleton maps correctly and can be retargeted where required.
- Facial controls, root motion, sockets, and constraints function in destination runtime.

## Animation acceptance

Review timing, spacing, weight, anticipation, follow-through, arcs, contacts, foot locking, hand/prop contact, secondary motion, acting, silhouette, transitions, loops, frame rate, root motion, clipping, and state-machine integration. Check at target runtime speed and camera framing. Provide pose sheets/contact sheets, animation curves, and engine capture where needed.

## Anti-pattern

A set of technically exported clips is not proof of animation quality. A rig that deforms poorly, has inconsistent scale, broken retargeting, or visible foot sliding fails acceptance even if the export file opens.
