#!/usr/bin/env python3
"""
ltx_director_onefile_3loras.py

Self-contained WhatDreamsCost LTX Director / LTX 2.3 ComfyUI runner.
- No external workflow JSON dependency: the API-format workflow is baked below.
- Keyframes are never hardcoded: pass them with --segment args.
- Global prompt is first-class: pass --global-prompt for the whole scene contract.
- No media verification: optional --wait only waits for ComfyUI history/output metadata.
- LoRA behavior in this 3-LoRA variant:
  - The original/base workflow LoRA is always loaded from DEFAULT_BASE_LORA.
  - DEFAULT_EXTRA_LORA_1/2/3 are blank optional slots for another agent to fill.
  - Blank extra LoRA slots are ignored; they do not get passed to ComfyUI.
  - If no extra LoRAs are filled, the model chain is: base model -> DEFAULT_BASE_LORA -> LTXDirector.
  - If extras are filled, the chain is: base model -> DEFAULT_BASE_LORA -> extra1 -> extra2 -> extra3 -> LTXDirector.

Typical usage:
  python3 ltx_director_onefile.py \
    --comfy-url http://127.0.0.1:8188 \
    --output-name jr_trailer_v01 \
    --fps 24 --width 1024 --height 1024 --seed 12345 \
    --global-prompt "same subject, same room, dark systems-noir, warm orange rim light, no text" \
    --negative-prompt "warped hands, flicker, identity drift, unreadable text, watermark" \
    --segment '0:4:/tmp/kf1.png:slow push in from behind as the subject codes quietly' \
    --segment '4:3.5:/tmp/kf2.png:side close-up of hands typing, coffee foreground' \
    --segment '7.5:3.5::text-only bridge through monitor glow and desk shadows' \
    --segment '11:4:/tmp/kf4.png:subject looks up into webcam calmly' \
    --submit --wait

Segment format:
  START_SECONDS:DURATION_SECONDS:KEYFRAME_PATH:PROMPT
Use an empty keyframe path for text-only clips:
  --segment '4:2.5::camera glides through orange monitor glow'

Prompt discipline for weaker agents:
- --global-prompt = identity, style, continuity, visual contract.
- each --segment prompt = visible action + camera motion for that beat.
- image generation/keyframe editing happens outside this script.
"""
from __future__ import annotations

import argparse
import base64
import copy
import json
import mimetypes
import os
import pathlib
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zlib
from dataclasses import dataclass
from typing import Any

DEFAULT_COMFY_URL = "http://127.0.0.1:8188"
DEFAULT_OUTPUT_NAME = "ltx_director_render"
DEFAULT_FPS = 24
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1024
DEFAULT_SEED = -1
DEFAULT_GLOBAL_PROMPT = ""
DEFAULT_NEGATIVE_PROMPT = ""

# Model defaults baked into the runner. Change these constants when a less capable
# agent needs a different default without remembering CLI flags.
DEFAULT_CHECKPOINT = "ltx2310eros_beta.safetensors"
DEFAULT_BASE_LORA = "ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors"
DEFAULT_BASE_LORA_STRENGTH = 0.5
DEFAULT_EXTRA_LORA_1 = ""
DEFAULT_EXTRA_LORA_2 = ""
DEFAULT_EXTRA_LORA_3 = ""
DEFAULT_EXTRA_LORA_STRENGTH_1 = 0.5
DEFAULT_EXTRA_LORA_STRENGTH_2 = 0.5
DEFAULT_EXTRA_LORA_STRENGTH_3 = 0.5
DEFAULT_CLIP1 = "gemma_3_12B_it_fp4_mixed.safetensors"
DEFAULT_CLIP2 = "ltx-2.3_text_projection_bf16.safetensors"
DEFAULT_UPSCALE_MODEL = "ltx-2.3-spatial-upscaler-x2-1.1.safetensors"

DEFAULT_GUIDE_STRENGTH = 1.0
DEFAULT_TIMEOUT_SECONDS = 60 * 60

# Baked API-format ComfyUI workflow. It is compressed only to keep this file compact.
# It comes from a working LTX 2.3 Director graph with the second-stage CropGuides tail-fix wiring.
EMBEDDED_WORKFLOW_ZLIB_BASE64 = "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"


def baked_workflow() -> dict[str, Any]:
    raw = zlib.decompress(base64.b64decode(EMBEDDED_WORKFLOW_ZLIB_BASE64)).decode("utf-8")
    return json.loads(raw)


@dataclass
class Segment:
    start_seconds: float
    duration_seconds: float
    image_path: str
    prompt: str

    @property
    def is_image(self) -> bool:
        return bool(self.image_path.strip())


def fail(msg: str, code: int = 2) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def http_json(method: str, url: str, payload: Any | None = None, timeout: int = 120) -> Any:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        fail(f"HTTP {e.code} from {url}: {detail}")
    except urllib.error.URLError as e:
        fail(f"Could not reach {url}: {e}")


def upload_image(comfy_url: str, path: str, overwrite: bool = True) -> str:
    p = pathlib.Path(path).expanduser().resolve()
    if not p.is_file():
        fail(f"Keyframe image does not exist: {p}")

    boundary = "----ltxonefile" + uuid.uuid4().hex
    mime = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
    filename = p.name
    parts: list[bytes] = []

    def field(name: str, value: str) -> None:
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())

    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n".encode()
    )
    parts.append(p.read_bytes())
    parts.append(b"\r\n")
    field("type", "input")
    field("overwrite", "true" if overwrite else "false")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)

    req = urllib.request.Request(
        comfy_url.rstrip("/") + "/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Content-Length": str(len(body))},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            res = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        fail(f"Image upload failed for {p}: HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        fail(f"Image upload failed for {p}: {e}")

    return res.get("name") or filename


def parse_segment(text: str) -> Segment:
    # Split only the first three ':' so prompts may contain colons.
    parts = text.split(":", 3)
    if len(parts) != 4:
        fail(f"Bad --segment format: {text!r}. Expected START:DURATION:IMAGE_PATH:PROMPT")
    start_s, dur_s, image_path, prompt = parts
    try:
        start = float(start_s)
        dur = float(dur_s)
    except ValueError:
        fail(f"Bad start/duration in --segment: {text!r}")
    if start < 0 or dur <= 0:
        fail(f"Segment start must be >=0 and duration >0: {text!r}")
    if not prompt.strip():
        fail(f"Segment prompt cannot be empty: {text!r}")
    return Segment(start, dur, image_path.strip(), prompt.strip())


def load_segments(args: argparse.Namespace) -> list[Segment]:
    segments: list[Segment] = []
    for s in args.segment or []:
        segments.append(parse_segment(s))

    if args.segment_json:
        raw = args.segment_json
        candidate = pathlib.Path(raw).expanduser()
        if candidate.exists():
            raw = candidate.read_text()
        data = json.loads(raw)
        if not isinstance(data, list):
            fail("--segment-json must be a JSON list or a path to a JSON list")
        for item in data:
            if not isinstance(item, dict):
                fail("Each --segment-json item must be an object")
            try:
                segments.append(
                    Segment(
                        float(item["start"]),
                        float(item.get("duration", item.get("length_seconds"))),
                        str(item.get("image", item.get("keyframe", "")) or ""),
                        str(item["prompt"]),
                    )
                )
            except KeyError as e:
                fail(f"Missing key in --segment-json item: {e}")

    if not segments:
        fail("Pass at least one --segment or --segment-json item")
    return sorted(segments, key=lambda x: x.start_seconds)


def find_node(workflow: dict[str, Any], class_type: str) -> tuple[str, dict[str, Any]]:
    matches = [(nid, n) for nid, n in workflow.items() if n.get("class_type") == class_type]
    if not matches:
        fail(f"Baked workflow does not contain node class {class_type}")
    return matches[0]


def nodes_by_class(workflow: dict[str, Any], class_type: str) -> list[tuple[str, dict[str, Any]]]:
    return [(nid, n) for nid, n in workflow.items() if n.get("class_type") == class_type]


def set_input_if_present(workflow: dict[str, Any], key: str, value: Any, classes: tuple[str, ...] | None = None) -> int:
    count = 0
    for node in workflow.values():
        if classes and node.get("class_type") not in classes:
            continue
        inputs = node.get("inputs", {})
        if key in inputs and not isinstance(inputs[key], list):
            inputs[key] = value
            count += 1
    return count


def configure_lora_chain(
    workflow: dict[str, Any],
    base_lora: tuple[str, float],
    extra_loras: list[tuple[str, float]],
) -> None:
    """Keep the base workflow LoRA, then optionally chain up to 3 extra LoRAs.

    The original LTX workflow intentionally loads one distilled/base LoRA. That
    base LoRA is hardcoded via DEFAULT_BASE_LORA and is always kept unless the
    caller deliberately changes --base-lora. Blank extra LoRA names are ignored
    and are not passed to ComfyUI.
    """
    lora_nodes = nodes_by_class(workflow, "LoraLoaderModelOnly")
    if not lora_nodes:
        return
    base_lora_id, base_lora_node = lora_nodes[0]
    base_name, base_strength = base_lora
    if not base_name.strip():
        fail("Base LoRA cannot be blank in the 3-LoRA variant. Edit DEFAULT_BASE_LORA or pass --base-lora.")

    # Remove any additional baked LoRA nodes, but keep the original/base one.
    for nid, _ in lora_nodes[1:]:
        workflow.pop(nid, None)

    base_inputs = base_lora_node.setdefault("inputs", {})
    base_inputs["lora_name"] = base_name.strip()
    base_inputs["strength_model"] = float(base_strength)

    previous = [base_lora_id, 0]
    active = [(name.strip(), float(strength)) for name, strength in extra_loras if name and name.strip()]
    for idx, (name, strength) in enumerate(active, start=1):
        nid = f"onefile_extra_lora_{idx}"
        workflow[nid] = {
            "inputs": {
                "lora_name": name,
                "strength_model": strength,
                "model": previous,
            },
            "class_type": "LoraLoaderModelOnly",
            "_meta": {"title": f"Optional Extra LoRA {idx}"},
        }
        previous = [nid, 0]

    # Rewire existing consumers of the base LoRA to the extra-chain tail. Skip
    # the generated extra LoRA nodes so extra1 still receives the base LoRA.
    for nid, node in workflow.items():
        if str(nid).startswith("onefile_extra_lora_"):
            continue
        for key, value in node.get("inputs", {}).items():
            if value == [base_lora_id, 0]:
                node["inputs"][key] = previous


def quote_view(filename: str) -> str:
    return "/api/view?filename=" + urllib.parse.quote(filename) + "&type=input&subfolder="


def build_timeline(
    segments: list[Segment],
    fps: int,
    global_prompt: str,
    prepend_global: bool,
    uploaded_names: dict[str, str],
    prefix: str,
) -> tuple[str, str, str, str, int, float]:
    timeline_segments = []
    local_prompts = []
    lengths = []
    strengths = []

    for idx, seg in enumerate(segments, start=1):
        start_frame = round(seg.start_seconds * fps)
        length_frames = round(seg.duration_seconds * fps)
        prompt = seg.prompt.strip()
        effective_prompt = (global_prompt.strip() + "\n\n" + prompt).strip() if prepend_global and global_prompt.strip() else prompt
        local_prompts.append(effective_prompt)
        lengths.append(str(length_frames))
        strengths.append(f"{DEFAULT_GUIDE_STRENGTH:.2f}")
        item: dict[str, Any] = {
            "id": f"{prefix}_{idx}",
            "start": start_frame,
            "length": length_frames,
            "prompt": effective_prompt,
            "type": "image" if seg.is_image else "text",
        }
        if seg.is_image:
            server_name = uploaded_names.get(seg.image_path) or pathlib.Path(seg.image_path).name
            item["imageFile"] = server_name
            item["imageB64"] = quote_view(server_name)
        timeline_segments.append(item)

    final_end = max(item["start"] + item["length"] for item in timeline_segments)
    duration_seconds = final_end / fps
    timeline = {"segments": timeline_segments, "audioSegments": []}
    return (
        json.dumps(timeline, ensure_ascii=False, separators=(",", ":")),
        " | ".join(local_prompts),
        ",".join(lengths),
        ",".join(strengths),
        final_end,
        duration_seconds,
    )


def patch_workflow(args: argparse.Namespace, uploaded_names: dict[str, str]) -> dict[str, Any]:
    wf = copy.deepcopy(baked_workflow())
    segments = load_segments(args)
    fps = int(args.fps)
    if fps <= 0:
        fail("--fps must be positive")

    prefix = args.output_name.replace("/", "_").replace(" ", "_")
    timeline_data, local_prompts, segment_lengths, guide_strength, computed_frames, computed_seconds = build_timeline(
        segments, fps, args.global_prompt or "", args.prepend_global_to_local, uploaded_names, prefix
    )

    duration_frames = args.duration_frames or (round(args.duration * fps) if args.duration else computed_frames)
    duration_seconds = duration_frames / fps

    _, director = find_node(wf, "LTXDirector")
    di = director.setdefault("inputs", {})
    di["global_prompt"] = args.global_prompt or ""
    di["duration_frames"] = int(duration_frames)
    di["duration_seconds"] = float(duration_seconds)
    di["timeline_data"] = timeline_data
    di["local_prompts"] = local_prompts
    di["segment_lengths"] = segment_lengths
    di["guide_strength"] = guide_strength
    di["frame_rate"] = fps
    di["custom_width"] = int(args.width)
    di["custom_height"] = int(args.height)
    if "use_custom_audio" in di:
        di["use_custom_audio"] = False

    # Save prefix.
    for _, node in nodes_by_class(wf, "SaveVideo"):
        node.setdefault("inputs", {})["filename_prefix"] = args.output_name

    # Seed: set all RandomNoise nodes.
    seed = int(args.seed)
    if seed < 0:
        seed = random.randint(0, 2**31 - 1)
    set_input_if_present(wf, "noise_seed", seed, ("RandomNoise",))

    # Negative prompt support is workflow-dependent. This baked graph mostly uses zeroed negative conditioning,
    # but set any obvious text fields if future node versions expose them.
    if args.negative_prompt:
        for key in ("negative_prompt", "negative", "text_negative"):
            set_input_if_present(wf, key, args.negative_prompt)

    configure_lora_chain(
        wf,
        (args.base_lora, args.base_lora_strength),
        [
            (args.extra_lora1, args.extra_lora1_strength),
            (args.extra_lora2, args.extra_lora2_strength),
            (args.extra_lora3, args.extra_lora3_strength),
        ],
    )

    # Model/control overrides. They patch only baked fields that exist.
    optional = {
        "ckpt_name": args.checkpoint,
        "vae_name": args.video_vae,
        "clip_name1": args.clip1,
        "clip_name2": args.clip2,
        "model_name": args.upscale_model,
        "steps": args.steps,
        "cfg": args.cfg,
        "scheduler": args.scheduler,
        "sampler_name": args.sampler,
        "denoise": args.denoise,
        "scale_by": args.director_guide_scale,
    }
    for key, value in optional.items():
        if value is not None:
            set_input_if_present(wf, key, value)

    # More specific two-stage controls when desired.
    schedulers = nodes_by_class(wf, "BasicScheduler")
    if args.stage1_steps is not None and len(schedulers) >= 1:
        schedulers[0][1]["inputs"]["steps"] = args.stage1_steps
    if args.stage2_steps is not None and len(schedulers) >= 2:
        schedulers[1][1]["inputs"]["steps"] = args.stage2_steps
    if args.stage2_denoise is not None and len(schedulers) >= 2:
        schedulers[1][1]["inputs"]["denoise"] = args.stage2_denoise

    # Preview rate follows fps where present.
    set_input_if_present(wf, "preview_rate", fps)
    return wf


def submit_prompt(comfy_url: str, workflow: dict[str, Any], client_id: str) -> str:
    res = http_json("POST", comfy_url.rstrip("/") + "/prompt", {"prompt": workflow, "client_id": client_id}, timeout=120)
    prompt_id = res.get("prompt_id")
    if not prompt_id:
        fail(f"ComfyUI did not return prompt_id: {res}")
    return prompt_id


def wait_history(comfy_url: str, prompt_id: str, timeout_s: int, poll_s: float = 3.0) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        hist = http_json("GET", comfy_url.rstrip("/") + "/history/" + urllib.parse.quote(prompt_id), timeout=60)
        if prompt_id in hist:
            return hist[prompt_id]
        time.sleep(poll_s)
    fail(f"Timed out waiting for prompt {prompt_id} after {timeout_s}s", code=1)


def summarize_outputs(history_item: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    outputs = history_item.get("outputs", {}) if isinstance(history_item, dict) else {}
    for node_id, node_out in outputs.items():
        if not isinstance(node_out, dict):
            continue
        for kind in ("images", "videos", "audio", "gifs"):
            for item in node_out.get(kind, []) or []:
                if isinstance(item, dict):
                    rec = {"node_id": node_id, "type": kind[:-1], **item}
                    out.append(rec)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Self-contained baked-workflow LTX Director ComfyUI runner.")
    ap.add_argument("--comfy-url", default=DEFAULT_COMFY_URL)
    ap.add_argument("--output-name", default=DEFAULT_OUTPUT_NAME, help="SaveVideo filename_prefix, e.g. video/my_render")
    ap.add_argument("--fps", type=int, default=DEFAULT_FPS)
    ap.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    ap.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    ap.add_argument("--duration", type=float, help="Optional total seconds override. Defaults to last segment end.")
    ap.add_argument("--duration-frames", type=int, help="Optional total frame override. Overrides --duration.")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED, help="-1 randomizes")
    ap.add_argument("--global-prompt", default=DEFAULT_GLOBAL_PROMPT)
    ap.add_argument("--negative-prompt", default=DEFAULT_NEGATIVE_PROMPT)
    ap.add_argument("--prepend-global-to-local", action="store_true", help="Also prepend global prompt into each local segment prompt.")
    ap.add_argument("--segment", action="append", help="START:DURATION:KEYFRAME_PATH:PROMPT. Repeatable.")
    ap.add_argument("--segment-json", help="JSON list or path. Items: start, duration, image/keyframe, prompt.")

    ap.add_argument("--dry-run", action="store_true", help="Print patched workflow JSON; do not upload or submit.")
    ap.add_argument("--save-workflow", help="Write patched workflow JSON to this path.")
    ap.add_argument("--submit", action="store_true", help="Upload keyframes and submit to ComfyUI.")
    ap.add_argument("--wait", action="store_true", help="Wait for ComfyUI history and print output metadata only; no media verification.")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    ap.add_argument("--client-id", default="ltx-director-onefile-" + uuid.uuid4().hex)

    # Model overrides for local installations with different names.
    ap.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT, help="Patch CheckpointLoaderSimple.ckpt_name. Defaults to DEFAULT_CHECKPOINT at top of file.")
    ap.add_argument("--base-lora", default=DEFAULT_BASE_LORA, help="Hardcoded base workflow LoRA. Defaults to DEFAULT_BASE_LORA at top of file and should usually stay enabled.")
    ap.add_argument("--base-lora-strength", type=float, default=DEFAULT_BASE_LORA_STRENGTH)
    ap.add_argument("--extra-lora1", default=DEFAULT_EXTRA_LORA_1, help="Optional extra LoRA slot 1. Blank disables it; default is DEFAULT_EXTRA_LORA_1 at top of file.")
    ap.add_argument("--extra-lora2", default=DEFAULT_EXTRA_LORA_2, help="Optional extra LoRA slot 2. Blank disables it; default is DEFAULT_EXTRA_LORA_2 at top of file.")
    ap.add_argument("--extra-lora3", default=DEFAULT_EXTRA_LORA_3, help="Optional extra LoRA slot 3. Blank disables it; default is DEFAULT_EXTRA_LORA_3 at top of file.")
    ap.add_argument("--extra-lora1-strength", type=float, default=DEFAULT_EXTRA_LORA_STRENGTH_1)
    ap.add_argument("--extra-lora2-strength", type=float, default=DEFAULT_EXTRA_LORA_STRENGTH_2)
    ap.add_argument("--extra-lora3-strength", type=float, default=DEFAULT_EXTRA_LORA_STRENGTH_3)
    ap.add_argument("--video-vae", help="Patch all vae_name fields. Use only if your graph expects one VAE override globally.")
    ap.add_argument("--clip1", default=DEFAULT_CLIP1, help="Patch DualCLIPLoader.clip_name1. Defaults to DEFAULT_CLIP1 at top of file.")
    ap.add_argument("--clip2", default=DEFAULT_CLIP2, help="Patch DualCLIPLoader.clip_name2. Defaults to DEFAULT_CLIP2 at top of file.")
    ap.add_argument("--upscale-model", default=DEFAULT_UPSCALE_MODEL, help="Patch latent upscale model_name. Defaults to DEFAULT_UPSCALE_MODEL at top of file.")

    # Sampling controls.
    ap.add_argument("--steps", type=int, help="Patch all BasicScheduler.steps")
    ap.add_argument("--stage1-steps", type=int)
    ap.add_argument("--stage2-steps", type=int)
    ap.add_argument("--cfg", type=float, help="Patch all CFGGuider.cfg")
    ap.add_argument("--sampler", help="Patch KSamplerSelect.sampler_name")
    ap.add_argument("--scheduler", help="Patch BasicScheduler.scheduler")
    ap.add_argument("--denoise", type=float, help="Patch all BasicScheduler.denoise")
    ap.add_argument("--stage2-denoise", type=float)
    ap.add_argument("--director-guide-scale", type=float, help="Patch LTXDirectorGuide.scale_by")

    args = ap.parse_args()

    # Upload only when submitting. Dry-run/save-workflow remain file-system independent except for parsing args.
    uploaded: dict[str, str] = {}
    if args.submit:
        for seg in load_segments(args):
            if seg.is_image and seg.image_path not in uploaded:
                uploaded[seg.image_path] = upload_image(args.comfy_url, seg.image_path)

    workflow = patch_workflow(args, uploaded)

    if args.save_workflow:
        path = pathlib.Path(args.save_workflow).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2))
        print(json.dumps({"saved_workflow": str(path)}, ensure_ascii=False))

    if args.dry_run:
        print(json.dumps(workflow, ensure_ascii=False, indent=2))

    if args.submit:
        prompt_id = submit_prompt(args.comfy_url, workflow, args.client_id)
        result = {"status": "submitted", "prompt_id": prompt_id, "client_id": args.client_id, "uploaded_images": uploaded}
        if args.wait:
            hist = wait_history(args.comfy_url, prompt_id, args.timeout)
            result["status"] = "completed"
            result["outputs"] = summarize_outputs(hist)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if not args.dry_run and not args.save_workflow and not args.submit:
        fail("Nothing to do. Use --dry-run, --save-workflow, and/or --submit.")


if __name__ == "__main__":
    main()
