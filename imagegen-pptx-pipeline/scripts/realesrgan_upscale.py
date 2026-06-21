#!/usr/bin/env python3
"""Upscale slide comps or icon assets with Python RealESRGANer on CPU."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import numpy as np
import torch
from basicsr.archs.rrdbnet_arch import RRDBNet
from PIL import Image
from realesrgan import RealESRGANer


TOOL = "python-realesrganer"
ENGINE = "RealESRGANer"
MODEL_NAME = "RealESRGAN_x4plus"
MODEL_FILE = "RealESRGAN_x4plus.pth"
VALID_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
DEFAULT_MODEL_PATHS = (
    "/opt/miniconda3/lib/python3.12/site-packages/weights/RealESRGAN_x4plus.pth",
    "assets/models/RealESRGAN_x4plus.pth",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def image_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(p for p in path.iterdir() if p.suffix.lower() in VALID_EXTS and p.is_file())
    raise SystemExit(f"input path does not exist: {path}")


def resolve_model_path(raw: str | None) -> Path:
    candidates: list[Path] = []
    if raw:
        candidates.append(Path(raw).expanduser())
    env_path = os.environ.get("REALESRGAN_X4PLUS_MODEL")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.extend(Path(item).expanduser() for item in DEFAULT_MODEL_PATHS)
    for candidate in candidates:
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        if candidate.exists() and candidate.name == MODEL_FILE:
            return candidate.resolve()
    searched = ", ".join(str(item) for item in candidates)
    raise SystemExit(f"{MODEL_FILE} not found. Pass --model-path or set REALESRGAN_X4PLUS_MODEL. Searched: {searched}")


def enforce_16x9(width: int, height: int, source: Path) -> None:
    ratio = width / max(height, 1)
    if abs(ratio - (16 / 9)) > 0.015:
        raise SystemExit(f"slide comp must be 16:9 before Real-ESRGAN upscale: {source} is {width}x{height}")


def build_upsampler(model_path: Path, *, tile: int, tile_pad: int, pre_pad: int) -> RealESRGANer:
    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    return RealESRGANer(
        scale=4,
        model_path=str(model_path),
        model=model,
        tile=tile,
        tile_pad=tile_pad,
        pre_pad=pre_pad,
        half=False,
        device=torch.device("cpu"),
    )


def compute_outscale(width: int, height: int, *, kind: str, target_width: int, target_height: int, target_min: int) -> float:
    if kind == "comp":
        return target_width / float(width)
    return max(target_min / float(min(width, height)), 1.0)


def resize_exact(im: Image.Image, width: int, height: int) -> Image.Image:
    if im.size == (width, height):
        return im
    return im.resize((width, height), Image.Resampling.LANCZOS)


def output_for(source: Path, input_root: Path, output_root: Path, explicit_output: Path | None) -> Path:
    if explicit_output and input_root.is_file():
        return explicit_output
    if input_root.is_dir():
        rel = source.relative_to(input_root)
        return output_root / rel.with_suffix(".png")
    return output_root


def upscale_one(
    upsampler: RealESRGANer,
    source: Path,
    output: Path,
    *,
    model_path: Path,
    kind: str,
    target_width: int,
    target_height: int,
    target_min: int,
    tile: int,
    tile_pad: int,
    pre_pad: int,
) -> dict:
    source = source.expanduser().resolve()
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as source_image:
        original = source_image.convert("RGBA" if source_image.mode in {"RGBA", "LA"} or "transparency" in source_image.info else "RGB")
    input_size = original.size
    if kind == "comp":
        enforce_16x9(input_size[0], input_size[1], source)

    outscale = compute_outscale(
        input_size[0],
        input_size[1],
        kind=kind,
        target_width=target_width,
        target_height=target_height,
        target_min=target_min,
    )

    alpha = None
    if original.mode == "RGBA":
        alpha = original.getchannel("A")
        rgb = Image.new("RGB", original.size, (255, 255, 255))
        rgb.paste(original.convert("RGB"), mask=alpha)
    else:
        rgb = original.convert("RGB")

    arr = np.array(rgb)
    upscaled_arr, _ = upsampler.enhance(arr, outscale=outscale)
    final_rgb = Image.fromarray(upscaled_arr).convert("RGB")
    realesrgan_size = final_rgb.size

    if kind == "comp":
        final = resize_exact(final_rgb, target_width, target_height).convert("RGB")
    else:
        if min(final_rgb.size) < target_min:
            factor = target_min / float(min(final_rgb.size))
            final_rgb = final_rgb.resize(
                (max(1, round(final_rgb.width * factor)), max(1, round(final_rgb.height * factor))),
                Image.Resampling.LANCZOS,
            )
        if alpha is not None:
            final_alpha = alpha.resize(final_rgb.size, Image.Resampling.LANCZOS)
            final = Image.merge("RGBA", (*final_rgb.split(), final_alpha))
        else:
            final = final_rgb.convert("RGBA")
    final.save(output)

    with Image.open(output) as final_image:
        output_size = final_image.size
    return {
        "status": "processed",
        "kind": kind,
        "tool": TOOL,
        "engine": ENGINE,
        "backend": "python",
        "model": MODEL_NAME,
        "model_file": MODEL_FILE,
        "model_path": str(model_path),
        "model_sha256": sha256(model_path),
        "device": "cpu",
        "half": False,
        "scale": 4,
        "outscale": outscale,
        "tile": tile,
        "tile_pad": tile_pad,
        "pre_pad": pre_pad,
        "input_path": str(source),
        "output_path": str(output),
        "input_sha256": sha256(source),
        "output_sha256": sha256(output),
        "input_px": {"width": input_size[0], "height": input_size[1]},
        "realesrgan_output_px": {"width": realesrgan_size[0], "height": realesrgan_size[1]},
        "output_px": {"width": output_size[0], "height": output_size[1]},
        "target_px": {"width": target_width, "height": target_height} if kind == "comp" else None,
        "target_min_px": target_min if kind == "icon" else None,
        "alpha_preserved": alpha is not None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input image or directory.")
    parser.add_argument("--output", required=True, help="Output image or directory.")
    parser.add_argument("--manifest", required=True, help="Manifest JSON to write.")
    parser.add_argument("--kind", choices=["comp", "icon"], required=True)
    parser.add_argument("--model-path", default=None, help=f"Path to {MODEL_FILE}. Defaults to REALESRGAN_X4PLUS_MODEL or known local paths.")
    parser.add_argument("--target-width", type=int, default=3840)
    parser.add_argument("--target-height", type=int, default=2160)
    parser.add_argument("--target-min", type=int, default=256)
    parser.add_argument("--tile", type=int, default=400)
    parser.add_argument("--tile-pad", type=int, default=12)
    parser.add_argument("--pre-pad", type=int, default=0)
    args = parser.parse_args()

    if args.tile <= 0:
        raise SystemExit("--tile must be positive for CPU RealESRGANer runs")
    model_path = resolve_model_path(args.model_path)
    input_root = Path(args.input).expanduser().resolve()
    output_root = Path(args.output).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve()
    files = image_files(input_root)
    if not files:
        raise SystemExit(f"no supported image files under {input_root}")

    upsampler = build_upsampler(model_path, tile=args.tile, tile_pad=args.tile_pad, pre_pad=args.pre_pad)
    items = []
    for source in files:
        destination = output_for(source, input_root, output_root, output_root if input_root.is_file() else None)
        items.append(
            upscale_one(
                upsampler,
                source,
                destination,
                model_path=model_path,
                kind=args.kind,
                target_width=args.target_width,
                target_height=args.target_height,
                target_min=args.target_min,
                tile=args.tile,
                tile_pad=args.tile_pad,
                pre_pad=args.pre_pad,
            )
        )
        print(f"SR_DONE {destination.name} {items[-1]['output_px']['width']}x{items[-1]['output_px']['height']}", flush=True)

    manifest = {
        "status": "processed",
        "tool": TOOL,
        "engine": ENGINE,
        "backend": "python",
        "model": MODEL_NAME,
        "model_file": MODEL_FILE,
        "model_path": str(model_path),
        "model_sha256": sha256(model_path),
        "device": "cpu",
        "half": False,
        "tile": args.tile,
        "tile_pad": args.tile_pad,
        "pre_pad": args.pre_pad,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "kind": args.kind,
        "input": str(input_root),
        "output": str(output_root),
        "items": items,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ALL_SR_DONE", flush=True)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
