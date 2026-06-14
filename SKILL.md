---
name: ltx-director
description: Generate LTX 2.3 video locally via ComfyUI's LTX Director — keyframe-driven image-to-video and text-to-video with a baked known-good runner. Use when asked to animate keyframes/stills into video, make AI video clips/b-roll/trailers/music-video shots, turn Ideogram/generated images into motion, create multi-beat timelines with per-segment prompts, or whenever LTX/LTXV/video generation comes up. Pairs with ideogram4 (keyframes) and watch-video (verification).
---

# ltx-director — directed LTX 2.3 video on the local ComfyUI

Core philosophy: **don't treat LTX as "generate random cool shots" — treat every
render as a small directed scene.** Anchor keyframes give visual truth, prompts give
motion, deliberate scope gives meaning, verification catches drift.

## The pipeline position

```
ideogram4  → composes the frame   (keyframes, palette, layout, text)
ltx-director → makes it move      (image-to-video / text-to-video beats)
hyperframes  → cuts it to time    (assembly, typography, beat-sync)
watch-video  → verifies           (contact sheets, tail inspection)
```

## Quick recipe

1. **Scene contract** (one paragraph): subject identity, environment, palette,
   lens language, duration, aspect, emotional arc.
2. **Keyframes via the ideogram4 skill.** For continuity across beats use the
   proven verbatim-identity-block + fixed-seed discipline (the manga recipe);
   for sibling variations of one composition, ideogram i2i at denoise ≤0.45.
   The **anchor** keyframe (the most identity/aesthetics-critical moment) gets
   generated and approved FIRST; siblings derive from it.
3. **Render** with the baked runner (all timeline fields auto-synced):

```bash
python3 ~/.claude/skills/ltx-director/scripts/ltx_director_onefile.py \
  --output-name video/my_clip \
  --fps 24 --width 832 --height 1216 --seed 21 \
  --global-prompt "identity, style, continuity, environment, palette contract" \
  --negative-prompt "warped hands, flicker, identity drift, watermark, unreadable text" \
  --segment '0:4:/abs/keyframe1.png:visible action + camera motion for beat one' \
  --segment '4:3::text-only bridge beat (empty keyframe path)' \
  --submit --wait
```

   Segment format `START:DURATION:KEYFRAME_PATH:PROMPT`; empty path = text-only
   beat. `--dry-run` / `--save-workflow` to inspect before submitting.
   ComfyUI default `http://127.0.0.1:8188`.
4. **Verify with watch-video**: 1fps overview collage + a dense pass on faces
   and the tail (`--interval 0.3` over the last 2s). ffprobe duration/frames —
   expect length+1-frame behavior at 24fps.

## Prompting rules (the big one)

**Write prompts as descriptions of the FINISHED rendered footage**, never as
instructions to an operator and never as prohibition lists:

- GOOD: "The finished close-up is crisp and cinematic. He exhales, blinks once,
  locks his eyes forward; rain streaks behind him while skin texture and
  reflections remain resolved. The camera pushes slightly closer."
- BAD: "Make him blink. Do not freeze. Camera should move closer. No blur."

Structure: finished-footage quality → subject's visible action/performance →
camera behavior → lighting/mood → continuity facts as positive visible details.
True negatives go in `--negative-prompt`, not in segment prompts.

## Frozen-subject prevention (persona/human shots)

Strong identity keyframes over-anchor people: the world moves but the subject
sits like a wax figure. Counter with a **motion contract** in the global prompt
("the subject is alive and moving naturally: breathing, blinks, gaze shifts,
small head turns, shoulder weight shifts, hands actively performing") + 2-4
observable performance actions per segment + anti-mannequin negatives
(`frozen subject, statue, mannequin, still photograph, unblinking eyes`).
Design beats where the subject *does* something — decision, reaction, tactile
work — not just sits in a cool environment. If still frozen, keep keyframes
constant and retry with `--prepend-global-to-local` and stage-2 denoise 0.55
(explicit experiment — default 0.42 is the locked quality recipe).

## Scene timing

- Keyframes that depict an action's IMPACT (press, grab, reveal, payoff) need a
  short **text-only lead-up segment** first, or the action starts pre-completed.
- Keyframes that already show the payoff: keep their segment very short
  (~0.5–1.0s) or LTX holds it like a PowerPoint slide.
- Endings need punctuation — a resolution tail (pull-away, arrival, light
  change), not an accidental fade.
- Readable text/title-card keyframes: keep segments ≤1.75s, prompt them as
  "almost-locked printed poster, microscopic parallax" — longer holds mutate
  typography into gibberish. Verify tails.

## Validated production lessons

First production render proved the payoff-hold pitfall AND its fix on the same
keyframe + seed: a 4s segment starting at an impact keyframe = PowerPoint
slide; restructured as **1.7s text-only lead-up → 0.9s impact keyframe → 2.4s
text-only resolution tail** (+ `--prepend-global-to-local` motion contract +
anti-slideshow negatives `static image, slow zoom on still, slideshow`) =
real progressing action with a motion-blur whip that cuts perfectly on a beat.
Note: LTX may compress a literal lead-up (subject can start mid-action) —
acceptable for montage; add an earlier grounded keyframe if takeoff must read.

**The strong-render shape:** text-only segments are the WEAK recipe — LTX
wanders/hallucinates there. The strongest known render used **3 image
keyframes, segments 3s/4s/3s** — LTX interpolates between visual
truths instead of inventing.

**KEYFRAME DELTAS ARE THE MOTION (the hardest-won lesson, 5-render A/B chain):**
near-identical keyframes = LTX correctly renders "nothing happens" (frozen clip
+ one tail spasm; motion metric ~3.6). Siblings must encode REAL pose/state
deltas spanning an action arc (e.g., flag furled low → mid-sweep → flying
overhead) → motion spreads through the whole clip aligned to the beats (metric
9.1, 2.5×). **Ideogram i2i CANNOT make pose-delta siblings** — it defends
composition even at denoise 0.6; use the MANGA METHOD instead: fresh ideogram
generations per keyframe with verbatim identity/scene/style blocks + same seed,
changing ONLY the action description and bboxes. Also ruled out by A/B: aspect
ratio was NOT the freeze cause (square exact-recipe froze identically with
identical keyframes). Dense crowds remain harder than single subjects — prefer
sparse/large-subject b-roll; use rights-cleared stock for mega-crowds.
One simple continuous action per segment, handheld-documentary language; save
multi-event choreography for the edit, not the prompt.

**MONTAGE DOCTRINE (the big simplifier):** for music-video /
montage b-roll, do NOT render 10s 3-keyframe scenes — render **5s 2-keyframe
single-scene clips** (segments 0:2.5 + 2.5:2.5, framing-locked, pose-only
delta). You need `target_length / 5s` clips. A 5s single-scene clip gets a
BINARY pass/dismiss verdict — no seams, no partial-range bookkeeping, ~1min
re-rolls. Reserve the 10s 3-keyframe shape for actual narrative scenes
(trailers, persona beats) where the multi-beat structure is the point.

**GLOBAL PROMPTS SUMMON WHAT THEY NAME:** a batch-wide global motion contract
that names mediums ("drifting smoke, rippling fabric, flickering light") will
INJECT those elements into every clip — smoke appears in living rooms, sunny
streets, offices. Keep batch globals element-agnostic: "every element already
in the frame moves naturally; nothing new enters the frame." Name specific
mediums only in per-clip local prompts, and only when the keyframe contains
them. Negative-prompt `smoke, explosion, fire` for clean-air scenes.

**FRAMING LOCK (round-4 law):** keyframe deltas must be POSE deltas, not
FRAMING deltas. If the three keyframes change shot scale or subject position
(close → wide, left → right), LTX renders TELEPORTS at segment boundaries and
the clip reads as 3 disconnected shots. Keep ONE subject bbox across all three
captions; change only the action. Add "single continuous handheld shot, the
camera holds the same framing throughout, no cuts" to the global prompt.
**Segment-coherence curation:** judge every render with a DENSE 10-frame sheet
(1s interval), not 3 thumbnails — thumbnails miss morphs, clones (subject
duplicating into rows), object mutations, and seam teleports. Treat each
3-keyframe render as up to 3 harvestable shots: use coherent sub-ranges, never
cut across a broken seam. Anti-clone negatives: `duplicate people, clones,
multiple copies of the same person, extra balls`.

## Baseline lock (do not vibe-tune quality)

The runner bakes a known-good recipe: graph topology, checkpoint
`ltx-2.3-22b-dev-fp8`, distilled LoRA, **stage-2 denoise 0.42**, guide strength
1.0, resolution path. **Safe to change:** prompts, segments, keyframes, seed,
fps, size, output name, CLI overrides. **Locked without explicit user
approval:** topology, model defaults, denoise/steps/sampler, guide strength.
When the user asks "what changed," answer with a diff, not an apology.
The 3-extra-LoRA variant is `scripts/ltx_director_onefile_3loras.py` — a
separate artifact; don't backport its experiments into the baseline.

## Verification checklist (before claiming success)

- ffprobe: actual dimensions + duration (requested ≠ actual)
- watch-video 1fps overview — every beat does its job, no identity drift
- dense tail sheet — no smearing/glitch frames (if tail is bad, suspect
  stage-2 `LTXVCropGuides` wiring before timing)
- face-visible beats at ~6-8fps density when blink/gaze quality matters
- audio (if LTX-generated): `ffmpeg -af volumedetect`; normalize if hot
