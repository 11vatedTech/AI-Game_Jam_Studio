# EMBERKEEP — Art Bible v1.0

**Studio:** 11vatedTech AI Game Jam Studio
**Project type:** first production vertical slice (P3 benchmark)
**Status:** art direction authored before manufacture (2026-11-04)

---

## 1. Logline

You are the last lamplighter of a drowning shrine-city. Carry what warmth remains.

## 2. Visual thesis

> **Every frame is a dark negative space pierced by one warm lantern.**

The environment is cool, desaturated and heavy. Light is scarce and *earned*. Warm colour is a
resource: it appears only where heat exists — the player's lantern, lit embers, the pylons.
Nothing else in the world may be warm.

This single rule makes the game legible at a glance, gives the player an instant read on progress,
and creates the emotional arc: cold world → small contained warmth → restored dawn.

## 3. Palette (restricted, 6 values)

| Token | Hex | Use |
|---|---|---|
| `ink` | `#0B1016` | deepest shadow, UI background |
| `slate` | `#1C2B33` | stone shadow, fog core |
| `mist` | `#3E5A63` | mid-tone stone, atmospheric haze |
| `bone` | `#D8CDBA` | UI type, worn stone highlights, dry cloth |
| `lantern` | `#FFC168` | lantern core, UI accent |
| `ember` | `#FF7A2F` | lit pylons, mote sparks, warmth critical |

**90/10 law:** ≤10% of any frame's area may be warm (hue 20–45°, high value). If a frame breaks
this, the lighting is wrong.

## 4. Form language

- **Verticality.** Arches, columns, terraces — the architecture pulls the eye up and out of frame.
- **Bevel everything.** No perfectly sharp 90° edges on stone or metal; a 2–4 cm worn bevel is the
  signature of the world's age.
- **Wear is directional.** Erosion runs downward; pitting, not grime. Nothing is "dirty", everything
  is *weathered*.
- **Silhouette test.** The lantern must read as a lantern at 64 px tall, and the pylon at 128 px.
- **Scale truth.** Lantern 0.42 m tall (held). Pylon 3.6 m. Player eye height 1.65 m. Terrace step 0.35 m.

## 5. Materials

| Surface | Base | Roughness | Metal | Notes |
|---|---|---|---|---|
| Wet basalt | `slate` → `mist` | 0.28–0.42 | 0.0 | darker where water pools; subtle vertical streaks |
| Aged brass | `#8A6A3C` | 0.38–0.55 | 1.0 | patina in crevices, polished on touch points |
| Lantern glass | `bone` | 0.08 | 0.0 | emissive `lantern` @ 5.5, alpha 0.55 |
| Water | `slate` | 0.05 | 0.0 | planar, normal-rippled, reflective at grazing angles |

No PBR value in this project may be guessed: every material is authored, versioned and reviewed.

## 6. Lighting

- **Key:** the player's lantern — warm point light, ~1.6 m radius, intensity driven by the warmth meter.
- **Fill:** cool hemisphere, 0.04–0.06 intensity. Never enough to flatten silhouette.
- **Rim:** single horizon glow at dusk (`mist` tinted), behind the architecture.
- **Fog:** volumetric, density 0.02, tinted `slate`; fog is the world's cold, and the lantern is the only
  thing that penetrates it.
- **Contrast:** value hierarchy — 80% of frame below 0.18 luminance. The brightest 2% is always a light source.

## 7. Camera & composition

- Fixed third-person, 3/4 isometric-flavoured: pitch −32°, yaw follows player with slow damping.
- FOV 38°. No roll. No shaky-cam.
- Composition: player lantern in the lower-third; one architectural vertical per frame; horizon never
  dead-centre.

## 8. UI

- Typeface: high-contrast serif for titles, uppercase, tracking +0.12 em; humanist sans for numbers.
- Colour: `bone` on `ink` @ 78% opacity. Accent = `lantern`.
- Layout: corner-anchored, generous negative space, hairline rules (1 px @ 1080p).
- **Forbidden:** filled panels, drop shadows, rounded-rect buttons, glow outlines, icon soup.
- Accessibility: minimum contrast 4.5:1, warmth meter also encoded as a bar length + pulse rate,
  all critical text ≥ 20 px at 1080p.

## 9. Motion language

- Lantern sway is a damped pendulum (period 1.4 s, amplitude falls with speed).
- Player moves at 2.6 m/s walk, 4.2 m/s sprint; acceleration 12 m/s², no instant stops.
- Ember motes drift on a 0.35 Hz sine with per-mote phase offset — never uniform bobbing.
- Pylon ignition is a 1.2 s ramp, not a pop: light intensity eases `out_cubic`.

## 10. Audio direction

- 60 BPM, sparse. Cello sustain + felt piano, minor mode, no percussion until the final ignition.
- Ambience: rain on stone, distant water, low wind through stone.
- Lantern: continuous soft flame bed; its volume rises as warmth falls (intimacy under threat).
- Ignition: warm swell (sub + brassy harmonic), 1.2 s. Mote pickup: single struck-glass note, randomised ±2 semitones.
- Loudness target: −16 LUFS integrated, true peak ≤ −1.5 dBTP.

## 11. Forbidden deviations

No neon/cyberpunk palettes. No purple-orange gradient sky. No lens flares or bloom abuse.
No cartoon outlines. No photoreal humans. No recognisable third-party IP, logos or characters.
No placeholder primitives presented as finished art.

## 12. Acceptance for this slice

A frame passes when: the lantern is the single brightest element; warm area ≤10%; the architecture
reads as ancient and vertical; the image survives at gameplay distance (1280×720) *and* at detail
(1920×1080); no visible UV seams on the hero asset; mesh normals are outward; the packaged build runs
at ≥60 fps at 1080p on the target workstation.
