# ltx-director

Directed **LTX 2.3** video generation on a local **ComfyUI**, as an installable agent skill.

Treats every render as a small **directed scene** — not "generate a random cool shot."
Anchor keyframes give visual truth, prompts give motion, deliberate scope gives meaning,
verification catches drift. The runner bakes a known-good LTX-Director workflow so an agent
(or you) only supplies prompts, segments, and keyframes — never graph topology.

## Pipeline position

```
keyframer (e.g. Ideogram/ComfyUI) → composes the frame   (keyframes, palette, layout)
ltx-director                       → makes it move        (image-to-video / text-to-video beats)
your editor (e.g. hyperframes)     → cuts it to time      (assembly, typography, beat-sync)
a video inspector                  → verifies             (contact sheets, tail inspection)
```

## What's in here

| path | what |
|---|---|
| `SKILL.md` | the craft contract — prompting rules, frozen-subject fixes, scene timing, montage doctrine, framing lock, baseline lock, verification checklist. **Read this; it's the value.** |
| `scripts/ltx_director_onefile.py` | the self-contained runner — the API-format LTX-Director workflow is baked in; you pass prompts/segments/keyframes via CLI |
| `scripts/ltx_director_onefile_3loras.py` | a 3-extra-LoRA variant (separate experiment; not the baseline) |
| `HANDOFF.md` | agent-agnostic guide (use the runner from any harness) |

## Requirements (reproducible setup)

1. **ComfyUI**, running and reachable (default `http://127.0.0.1:8188`).
2. The **WhatDreamsCost LTX Director** custom nodes for ComfyUI
   (the `LTXDirector` / `LTXDirectorGuide` / `LTXVCropGuides` node family).
   Tail-frame artifact fix: route the final `LTXVCropGuides` positive/negative from the
   **second-stage** `LTXDirectorGuide`, not the first-stage guide.
3. **LTX 2.3 models** placed in ComfyUI's model folders (the runner's baked defaults — override
   with the matching CLI flags if your filenames differ):
   - checkpoint `ltx-2.3-22b-dev-fp8.safetensors`
   - distilled LoRA `ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors`
   - text encoders `gemma_3_12B_it_fp4_mixed.safetensors`, `ltx-2.3_text_projection_bf16.safetensors`
4. **Python 3** (standard library only — no pip dependencies; the runner talks to ComfyUI over HTTP).

Point the runner at a non-local ComfyUI with `--comfy-url http://HOST:PORT`.

## Usage

```bash
python3 scripts/ltx_director_onefile.py \
  --comfy-url http://127.0.0.1:8188 \
  --output-name video/my_clip \
  --fps 24 --width 832 --height 1216 --seed 21 \
  --global-prompt "subject identity, style, continuity, environment, palette contract" \
  --negative-prompt "warped hands, flicker, identity drift, watermark, unreadable text" \
  --segment '0:4:/abs/keyframe1.png:visible action + camera motion for beat one' \
  --segment '4:3::text-only bridge beat (empty keyframe path)' \
  --submit --wait
```

- **Segment format:** `START_SECONDS:DURATION_SECONDS:KEYFRAME_PATH:PROMPT` — empty keyframe
  path = text-only beat.
- `--dry-run` / `--save-workflow` to inspect the graph before submitting.
- **Safe to change:** prompts, segments, keyframes, seed, fps, size, output name.
  **Baseline-locked** (don't vibe-tune): graph topology, model defaults, denoise/steps/sampler,
  guide strength — these encode the known-good quality recipe.

The single biggest rule (full version in `SKILL.md`): **write prompts as descriptions of the
FINISHED rendered footage, not as instructions to an operator and not as prohibition lists.**
True negatives go in `--negative-prompt`.

## Install as a skill

Claude Code / Agent Skills hosts: drop this repo's folder into your skills directory (e.g.
`~/.claude/skills/ltx-director`), or symlink it. The skill is invoked by the model when LTX /
video generation comes up; humans can run the script directly.

## License

Skill code + notes: **MIT** (see `LICENSE`). The **LTX-Video 2.3** model weights are governed
by Lightricks' own license — obtain and use them under their terms; this repo ships no weights.
