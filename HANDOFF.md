# ltx-director — agent handoff

Agent-agnostic guide. Any harness that can run shell commands and read files can drive the
runner; `SKILL.md` is the Claude Code reference but the contract below is harness-neutral.
For tool names, map to your harness: "run a shell command" = Bash/exec/shell; "read a file" =
Read/cat.

## The contract

1. **Read `SKILL.md` first** — it's the craft, not boilerplate. The load-bearing rules:
   - Write prompts as descriptions of the **finished rendered footage**, never as operator
     instructions or prohibition lists. True negatives go in `--negative-prompt`.
   - **Keyframe deltas ARE the motion** — near-identical keyframes render "nothing happens."
     Siblings must encode real pose/state deltas across an action arc.
   - **Framing lock** — keyframe deltas are POSE deltas, not framing deltas, or LTX teleports
     at segment boundaries. One subject bbox across keyframes; change only the action.
   - **Frozen-subject fix** for human/persona shots: a motion contract in the global prompt +
     2–4 observable actions per segment + anti-mannequin negatives.
   - **Baseline lock** — topology, model defaults, denoise/steps/sampler, guide strength are
     locked. Only prompts/segments/keyframes/seed/fps/size/output are the safe surface.
2. **Generate keyframes elsewhere** (any image tool). This runner does image-to-video, not
   image generation. The anchor keyframe (most identity-critical moment) is made and approved
   first; siblings derive from it.
3. **Render** with the runner (see below).
4. **Verify before claiming success** — `ffprobe` actual dimensions/duration, then a frame
   contact sheet: every beat does its job, no identity drift, no smeared/glitch tail frames.
   Expect `frames = requested_frames + 1` at the LTX-Director level.

## Run it

```bash
python3 scripts/ltx_director_onefile.py \
  --comfy-url http://HOST:PORT \
  --output-name <name> --fps 24 --width <W> --height <H> --seed <N> \
  --global-prompt "<identity / style / continuity / palette contract>" \
  --negative-prompt "<true negatives>" \
  --segment 'START:DURATION:KEYFRAME_PATH:PROMPT' \
  --segment 'START:DURATION::TEXT-ONLY PROMPT' \
  --submit --wait
```

- Default `--comfy-url` is `http://127.0.0.1:8188`.
- Segment = `START_SECONDS:DURATION_SECONDS:KEYFRAME_PATH:PROMPT`; empty keyframe path = text-only beat.
- Inspect first with `--dry-run` or `--save-workflow` (writes the API-format graph without submitting).
- Exit code is non-zero on submit/connection failure; `--wait` polls ComfyUI history for completion.

## Requirements

ComfyUI reachable + the WhatDreamsCost LTX Director custom nodes + LTX 2.3 models in ComfyUI's
model folders (filenames in `README.md`; override via CLI flags if yours differ). Python 3 stdlib
only — no pip installs.

## Boundaries

- The runner submits a render job to ComfyUI; it does not verify the output media. Always run a
  separate verification pass (ffprobe + contact sheet).
- Text-only segments are the weak recipe — LTX wanders there. Prefer at least one image keyframe;
  the strongest shape is multiple image keyframes with real pose deltas.
