from __future__ import annotations

import importlib.util
import json
import subprocess
import struct
import sys
import tempfile
import unittest
from pathlib import Path


MIN_COMP_BYTES = 5 * 1024 * 1024
REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "imagegen-pptx-pipeline"
INIT_SCRIPT = SKILL_DIR / "scripts" / "init_pipeline_workspace.py"
GATE_SCRIPT = SKILL_DIR / "scripts" / "check_pipeline_gates.py"
COMP_ASSET_SCRIPT = SKILL_DIR / "scripts" / "check_imagegen_comp_asset.py"
NORMALIZE_SCRIPT = SKILL_DIR / "scripts" / "normalize_slide_comp.py"
ICON_SCRIPT = SKILL_DIR / "scripts" / "prepare_icon_assets.py"
AUDIT_SCRIPT = SKILL_DIR / "scripts" / "audit_pptx_reconstruction.py"


def load_gate_module():
    spec = importlib.util.spec_from_file_location("check_pipeline_gates", GATE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def run_json(args: list[str], *, check: bool = True) -> dict:
    completed = subprocess.run(args, check=check, text=True, capture_output=True)
    return json.loads(completed.stdout)


def quality_policy() -> dict:
    return {
        "policy_id": "imagegen-max-clarity-v1",
        "enabled": True,
        "prompt_detail_level": "highest_available",
        "requested_single_slide_canvas_px": {"width": 3840, "height": 2160},
        "minimum_acceptable_comp_px": {"width": 3840, "height": 2160},
        "minimum_acceptable_comp_bytes": MIN_COMP_BYTES,
        "postprocess_policy": {
            "enabled": True,
            "normalize_every_comp": True,
            "target_px": {"width": 3840, "height": 2160},
            "local_repair_script": "scripts/normalize_slide_comp.py",
            "save_raw_imagegen_output": True,
            "same_output_dimensions_required": True,
            "downstream_uses_normalized_comp": True,
        },
        "minimum_acceptable_contact_sheet_px": {"width": 2400, "height": 1350},
        "prompt_requires_crisp_text_and_icons": True,
        "review_required_before_pptx": True,
        "small_text_policy": "Keep text and icons sharp; exact final small text is rebuilt from deck_spec.",
        "blur_rejection_criteria": ["blurry title", "muddy icons", "soft fine lines"],
    }


def failure_policy() -> dict:
    return {
        "policy_id": "imagegen-fail-closed-v1",
        "enabled": True,
        "fail_closed": True,
        "max_retries_per_asset": 2,
        "prompt_compression_allowed": True,
        "prompt_compression_scope": [
            "remove duplicated source prose",
            "remove internal reasoning",
            "remove repeated constraints",
            "summarize verbose citations while preserving source IDs",
        ],
        "prompt_compression_must_preserve": [
            "locked slide order",
            "slide titles",
            "core claims",
            "required data",
            "proof-object intent",
            "template constraints",
            "visual density floor",
            "aesthetic family",
        ],
        "content_density_may_be_reduced": False,
        "visual_complexity_may_be_reduced": False,
        "html_surrogate_allowed": False,
        "generic_ppt_fallback_allowed": False,
        "block_after_repeated_failures": True,
        "retry_log_path": "imagegen_retry_log.json",
    }


def clarity_review() -> dict:
    return {
        "status": "approved",
        "image_dimensions_px": {"width": 3840, "height": 2160},
        "image_file_size_bytes": MIN_COMP_BYTES,
        "text_legibility": "approved",
        "icon_line_clarity": "approved",
        "edge_sharpness": "approved",
        "blocking_blur": False,
        "small_text_strategy": "Small text is either readable in the comp or rebuilt exactly during PPTX reconstruction.",
    }


def style_continuity_review() -> dict:
    return {
        "status": "approved",
        "matches_comp_style_lock": True,
        "page_chrome_consistent": True,
        "recurring_elements_consistent": True,
        "issues": [],
    }


def visual_contract_generation_defaults() -> dict:
    return {
        "comp_generation_mode": "main_agent_serial_imagegen",
        "parallel_style_agents_used": False,
        "parallel_page_subagents_used": False,
        "explicit_parallel_comp_generation_accepted": False,
        "comp_style_lock": {
            "source": "selected contact sheet + first approved comp",
            "dimensions_px": {"width": 3840, "height": 2160},
            "chrome_locked": True,
            "locked_chrome_elements": [
                "logo",
                "section label",
                "header rule",
                "footer",
                "page number",
                "page marker",
                "title furniture",
            ],
            "consistency_requirements": [
                "same page number placement and format",
                "same logo placement and size",
                "same header/footer system",
                "same section label treatment",
                "same recurring typography scale",
                "same border/background/chrome rhythm",
            ],
            "generation_owner": "main_agent",
        },
        "icon_asset_policy": {
            "enabled": True,
            "manifest_path": "assets/icon-manifests/icon_asset_manifest.json",
            "processor_script": "scripts/prepare_icon_assets.py",
            "transparent_png_required": True,
            "minimum_transparent_padding_px": 16,
            "crop_expansion_px": 12,
            "minimum_output_icon_px": 256,
            "forbid_edge_touching_colored_pixels": True,
            "use_processed_icons_in_pptx": True,
        },
        "pptx_render_fix_loop": {
            "enabled": True,
            "minimum_rounds": 9,
            "rounds_log_path": "qa/render-fix/render_fix_rounds.json",
            "block_on_unresolved_p0_p1": True,
        },
        "pptx_native_reconstruction_policy": native_reconstruction_policy(),
        "default_reconstruction_mode": "native_trace_hybrid",
        "native_trace_hybrid_required": True,
        "pixel_locked_hybrid_required": False,
    }


def native_reconstruction_policy() -> dict:
    return {
        "enabled": True,
        "audit_script": "scripts/audit_pptx_reconstruction.py",
        "report_path": "qa/pptx-reconstruction-audit.json",
        "require_native_trace_hybrid_by_default": True,
        "source_image_is_coordinate_blueprint": True,
        "source_image_may_not_be_retained_as_full_slide_layer": True,
        "allow_full_slide_backplate_by_default": False,
        "max_full_slide_or_large_raster_images_per_slide": 0,
        "full_slide_or_large_picture_area_ratio": 0.85,
        "content_slide_thresholds": {
            "minimum_native_elements": 35,
            "minimum_visible_text_shapes": 8,
            "minimum_editable_text_chars": 60,
        },
        "simple_slide_thresholds": {
            "minimum_native_elements": 10,
            "minimum_visible_text_shapes": 2,
            "minimum_editable_text_chars": 10,
        },
    }


def native_trace_plan(*, simple: bool = True) -> dict:
    return {
        "source_image_used_as_coordinate_reference": True,
        "source_image_used_as_coordinate_blueprint": True,
        "source_image_not_retained_as_full_slide_layer": True,
        "pixel_to_inch_mapping_recorded": True,
        "native_element_count": 16 if simple else 80,
        "visible_text_box_count": 4 if simple else 14,
        "editable_text_char_count": 40 if simple else 180,
        "render_fix_verify_loop": True,
        "retained_image_exceptions": [],
    }


def native_overlay_plan(*, count: int = 4) -> dict:
    return {
        "visible_native_text_overlay": True,
        "visible_overlay_count": count,
        "native_shape_count": 40,
        "regions": ["editable title", "editable body", "editable key number", "editable footer"],
    }


def normalization_record(idx: int = 1) -> dict:
    return {
        "status": "completed",
        "raw_imagegen_output_path": f"slides/raw/slide-{idx:03d}-imagegen.png",
        "output_path": f"slides/slide-{idx:03d}-comp.png",
        "output_dimensions_px": {"width": 3840, "height": 2160},
        "local_repair_applied": True,
        "script_path": "scripts/normalize_slide_comp.py",
    }


def write_gate_scaffolding(workspace: Path) -> None:
    (workspace / "assets" / "icon-manifests").mkdir(parents=True, exist_ok=True)
    (workspace / "assets" / "icon-manifests" / "icon_asset_manifest.json").write_text(
        json.dumps({"status": "draft", "icons": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (workspace / "qa" / "render-fix").mkdir(parents=True, exist_ok=True)
    (workspace / "qa" / "render-fix" / "render_fix_rounds.json").write_text(
        json.dumps(
            {"status": "not_started", "minimum_rounds": 9, "completed_rounds": 0, "rounds": [], "unresolved_p0_p1": []},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (workspace / "slides" / "raw").mkdir(parents=True, exist_ok=True)


def fake_png(width: int = 3840, height: int = 2160, min_bytes: int = MIN_COMP_BYTES) -> bytes:
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + struct.pack(">II", width, height)
        + b"\x08\x02\x00\x00\x00"
        + b"\x00\x00\x00\x00"
    )
    if min_bytes and len(payload) < min_bytes:
        payload += b"\0" * (min_bytes - len(payload))
    return payload


def taste_guidance() -> dict:
    return {
        "enabled": True,
        "sources": [
            {"name": "built-in-ppt-taste-system", "path": "references/taste-system.md"},
            {"name": "built-in-ppt-style-library", "path": "references/style-library.md"},
        ],
    }


def style_library() -> dict:
    return {
        "enabled": True,
        "sources": [
            {"name": "built-in-ppt-style-library", "path": "references/style-library.md"},
        ],
        "style_options_must_remain_visual_only": True,
        "must_not_use_third_party_logos_without_assets": True,
    }


class PipelineSmokeTests(unittest.TestCase):
    def test_imagegen_comp_prompt_preflight_requires_hard_quality_constraints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prompt = Path(tmp) / "slide-001-comp.txt"
            prompt.write_text(
                "Generate one true 4K 3840x2160 slide comp with highest detail. "
                "The saved PNG must be at least 5 MiB / 5242880 bytes, use the same pixel dimensions "
                "as every other page, and have crisp sharp text/icons/fine lines with no blur. "
                "If the service cannot produce 4K, fallback to 2K 2560x1440, then 1080p 1920x1080; "
                "do not retry forever and keep the output as high as possible.",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [sys.executable, str(COMP_ASSET_SCRIPT), "--prompt", str(prompt), "--require-fallback-policy"],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            prompt.write_text("Generate a nice slide.", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(COMP_ASSET_SCRIPT), "--prompt", str(prompt)],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("3840 width", completed.stderr)
            self.assertIn("tier file-size minimum", completed.stderr)

            prompt.write_text(
                "Generate one true 4K 3840x2160 slide comp with highest detail. "
                "The saved PNG must be at least 5 MiB / 5242880 bytes, use the same pixel dimensions "
                "as every other page, and have crisp sharp text/icons/fine lines with no blur.",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [sys.executable, str(COMP_ASSET_SCRIPT), "--prompt", str(prompt), "--require-fallback-policy"],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("2K fallback", completed.stderr)
            self.assertIn("1080p fallback", completed.stderr)

    def test_imagegen_comp_asset_check_accepts_2k_fallback_for_4k_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prompt = Path(tmp) / "slide-001-comp.txt"
            image = Path(tmp) / "slide-001-comp.png"
            prompt.write_text(
                "Generate one true 4K 3840x2160 slide comp with highest detail. "
                "The saved PNG must be at least 5 MiB / 5242880 bytes, use identical pixel dimensions "
                "across the deck, and have crisp sharp text/icons/fine lines with no blur. "
                "If 4K is unavailable, fallback to 2K 2560x1440, then 1080p 1920x1080; "
                "do not retry forever and keep it as high as possible.",
                encoding="utf-8",
            )
            image.write_bytes(fake_png(2560, 1440, min_bytes=2 * 1024 * 1024))
            completed = subprocess.run(
                [
                    sys.executable,
                    str(COMP_ASSET_SCRIPT),
                    "--prompt",
                    str(prompt),
                    "--image",
                    str(image),
                    "--allow-fallback",
                ],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("PASS_WITH_FALLBACK tier=2k", completed.stdout)

    def test_imagegen_comp_asset_check_rejects_low_resolution_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prompt = Path(tmp) / "slide-001-comp.txt"
            image = Path(tmp) / "slide-001-comp.png"
            prompt.write_text(
                "Generate one true 4K 3840x2160 slide comp with highest detail. "
                "The saved PNG must be at least 5 MiB / 5242880 bytes, use identical pixel dimensions "
                "across the deck, and have crisp sharp text/icons/fine lines with no blur. "
                "If 4K is unavailable, fallback to 2K 2560x1440, then 1080p 1920x1080; "
                "do not retry forever and keep it as high as possible.",
                encoding="utf-8",
            )
            image.write_bytes(fake_png(1672, 941, min_bytes=MIN_COMP_BYTES))
            completed = subprocess.run(
                [
                    sys.executable,
                    str(COMP_ASSET_SCRIPT),
                    "--prompt",
                    str(prompt),
                    "--image",
                    str(image),
                    "--allow-fallback",
                ],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("1920x1080", completed.stderr)
            self.assertIn("1672x941", completed.stderr)

    def test_normalize_slide_comp_outputs_uniform_4k(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "raw.png"
            output = Path(tmp) / "slide-001-comp.png"
            report = Path(tmp) / "normalization.json"
            Image.new("RGB", (1672, 941), (255, 255, 255)).save(source)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(NORMALIZE_SCRIPT),
                    "--input",
                    str(source),
                    "--output",
                    str(output),
                    "--manifest",
                    str(report),
                ],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            with Image.open(output) as image:
                self.assertEqual(image.size, (3840, 2160))
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["output_dimensions_px"], {"width": 3840, "height": 2160})
            self.assertTrue(payload["sharpen_after_resize"])

    def test_prepare_icon_assets_outputs_transparent_padded_png(self) -> None:
        from PIL import Image, ImageDraw

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            source = workspace / "slides" / "style-lane-A" / "slide-001-comp.png"
            source.parent.mkdir(parents=True)
            image = Image.new("RGBA", (400, 300), (255, 255, 255, 255))
            draw = ImageDraw.Draw(image)
            draw.rectangle((120, 90, 170, 140), fill=(220, 0, 0, 255))
            image.save(source)
            manifest = workspace / "assets" / "icon-manifests" / "icon_asset_manifest.json"
            manifest.parent.mkdir(parents=True)
            output = workspace / "assets" / "icons" / "style-lane-A" / "slide-001-icon-01.png"
            manifest.write_text(
                json.dumps(
                    {
                        "status": "ready",
                        "default_padding_px": 16,
                        "default_crop_expansion_px": 12,
                        "white_threshold": 246,
                        "minimum_output_icon_px": 256,
                        "icons": [
                            {
                                "id": "slide-001-icon-01",
                                "source_image_path": "slides/style-lane-A/slide-001-comp.png",
                                "bbox_px": {"left": 112, "top": 82, "width": 70, "height": 70},
                                "output_path": "assets/icons/style-lane-A/slide-001-icon-01.png",
                                "padding_px": 16,
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            report = workspace / "assets" / "icon-manifests" / "icon_asset_report.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ICON_SCRIPT),
                    "--manifest",
                    str(manifest),
                    "--workspace",
                    str(workspace),
                    "--report",
                    str(report),
                    "--strict",
                ],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            with Image.open(output) as icon:
                self.assertEqual(icon.mode, "RGBA")
                self.assertEqual(icon.getpixel((0, 0))[3], 0)
                self.assertGreaterEqual(icon.size[0], 256)
                self.assertGreaterEqual(icon.size[1], 256)
                alpha_bbox = icon.getchannel("A").getbbox()
                self.assertIsNotNone(alpha_bbox)
                assert alpha_bbox is not None
                self.assertGreater(alpha_bbox[0], 0)
                self.assertGreater(alpha_bbox[1], 0)
                self.assertLess(alpha_bbox[2], icon.size[0])
                self.assertLess(alpha_bbox[3], icon.size[1])
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "completed")
            self.assertTrue(payload["results"][0]["transparent_background"])
            self.assertTrue(payload["results"][0]["edge_clear"])

    def test_pptx_reconstruction_audit_rejects_full_slide_image_only(self) -> None:
        from PIL import Image
        from pptx import Presentation
        from pptx.util import Inches

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            image = tmp_path / "source.png"
            Image.new("RGB", (1920, 1080), (240, 240, 240)).save(image)
            pptx_path = tmp_path / "image-only.pptx"
            prs = Presentation()
            prs.slide_width = Inches(13.333333)
            prs.slide_height = Inches(7.5)
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            slide.shapes.add_picture(str(image), 0, 0, width=prs.slide_width, height=prs.slide_height)
            prs.save(pptx_path)

            completed = subprocess.run(
                [sys.executable, str(AUDIT_SCRIPT), "--pptx", str(pptx_path)],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 1)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "FAIL")
            self.assertTrue(any("large/full-slide raster" in item for item in payload["failures"]))

    def test_pptx_reconstruction_audit_accepts_native_dense_slide(self) -> None:
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.util import Inches, Pt

        with tempfile.TemporaryDirectory() as tmp:
            pptx_path = Path(tmp) / "native-dense.pptx"
            prs = Presentation()
            prs.slide_width = Inches(13.333333)
            prs.slide_height = Inches(7.5)
            slide = prs.slides.add_slide(prs.slide_layouts[6])

            for row in range(5):
                for col in range(7):
                    shape = slide.shapes.add_shape(
                        MSO_SHAPE.ROUNDED_RECTANGLE,
                        Inches(0.4 + col * 1.75),
                        Inches(1.2 + row * 0.75),
                        Inches(1.45),
                        Inches(0.42),
                    )
                    shape.text = f"Native card {row}-{col}"

            for idx in range(10):
                box = slide.shapes.add_textbox(
                    Inches(0.5 + (idx % 5) * 2.4),
                    Inches(0.2 + (idx // 5) * 0.45),
                    Inches(2.1),
                    Inches(0.3),
                )
                run = box.text_frame.paragraphs[0].add_run()
                run.text = f"Editable text block {idx}"
                run.font.size = Pt(12)
            prs.save(pptx_path)

            completed = subprocess.run(
                [sys.executable, str(AUDIT_SCRIPT), "--pptx", str(pptx_path)],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "PASS")
            self.assertGreaterEqual(payload["summary"]["total_native_elements"], 35)
            self.assertGreaterEqual(payload["summary"]["total_editable_text_shapes"], 8)

    def test_init_workspace_creates_slide_intent_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_json(
                [
                    sys.executable,
                    str(INIT_SCRIPT),
                    "--slug",
                    "smoke",
                    "--title",
                    "Smoke Deck",
                    "--mode",
                    "create",
                    "--root",
                    tmp,
                ]
            )
            workspace = Path(result["workspace"])
            self.assertTrue((workspace / "pipeline_state.json").exists())
            self.assertTrue((workspace / "deck_spec.json").exists())
            self.assertTrue((workspace / "slide_intent_plan.json").exists())
            self.assertTrue((workspace / "slide_intent_matrix.md").exists())
            self.assertTrue((workspace / "narrative_plan.json").exists())
            self.assertTrue((workspace / "reconstruction_manifest.json").exists())
            self.assertTrue((workspace / "imagegen_retry_log.json").exists())
            style_brief = json.loads((workspace / "style_brief.json").read_text(encoding="utf-8"))
            self.assertTrue(style_brief["imagegen_failure_policy"]["fail_closed"])

    def test_init_workspace_accepts_reconstruction_only_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_json(
                [
                    sys.executable,
                    str(INIT_SCRIPT),
                    "--slug",
                    "reconstruct",
                    "--title",
                    "Reconstruct Deck",
                    "--mode",
                    "reconstruction-only",
                    "--root",
                    tmp,
                ]
            )
            workspace = Path(result["workspace"])
            manifest = json.loads((workspace / "reconstruction_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "reconstruction-only")
            self.assertTrue(manifest["page_sharding"]["enabled"])

    def test_slide_intent_gate_fails_when_not_locked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_json(
                [
                    sys.executable,
                    str(INIT_SCRIPT),
                    "--slug",
                    "gate-fail",
                    "--title",
                    "Gate Fail Deck",
                    "--mode",
                    "create",
                    "--root",
                    tmp,
                ]
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--workspace",
                    result["workspace"],
                    "--stage",
                    "slide-intent-lock",
                ],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "FAIL")
            self.assertTrue(any("slide_intent_plan.json lock_state" in item for item in payload["failures"]))

    def test_slide_intent_gate_passes_minimal_locked_workspace(self) -> None:
        gate_module = load_gate_module()
        with tempfile.TemporaryDirectory() as tmp:
            result = run_json(
                [
                    sys.executable,
                    str(INIT_SCRIPT),
                    "--slug",
                    "gate-pass",
                    "--title",
                    "Gate Pass Deck",
                    "--mode",
                    "create",
                    "--root",
                    tmp,
                ]
            )
            workspace = Path(result["workspace"])
            deck_spec = json.loads((workspace / "deck_spec.json").read_text(encoding="utf-8"))
            deck_spec["deck"].update(
                {
                    "audience": "executive",
                    "objective": "approve launch",
                    "deck_profile": "product-pitch",
                    "content_input_type": "brief_outline",
                    "slide_count": 1,
                    "lock_state": "locked",
                }
            )
            deck_spec["slides"] = [
                {
                    "slide_id": "slide-001",
                    "page_number": 1,
                    "section": "opening",
                    "title": "Launch decision",
                    "claim": "The launch is ready for executive approval.",
                    "body_text": ["Decision request and readiness summary."],
                    "data": [],
                    "proof_object": "decision scorecard",
                    "visual_intent": "executive decision summary",
                    "template_source_slide": "",
                }
            ]
            (workspace / "deck_spec.json").write_text(
                json.dumps(deck_spec, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            fingerprint = gate_module.deck_spec_fingerprint(deck_spec)
            slide_intent = json.loads((workspace / "slide_intent_plan.json").read_text(encoding="utf-8"))
            slide_intent.update(
                {
                    "lock_state": "locked",
                    "source_deck_spec_fingerprint": fingerprint,
                    "review_status": "approved",
                    "slides": [
                        {
                            "slide_id": "slide-001",
                            "page_number": 1,
                            "proposed_title": "Launch decision",
                            "confirmed_title": "Launch decision",
                            "core_idea": "The launch can be approved because readiness is sufficient.",
                            "proof_goal": "Show the committee the decision and supporting readiness signal.",
                            "content_scope": "Decision request only.",
                            "evidence_candidates": [
                                {
                                    "source_id": "user_brief",
                                    "source_path": "",
                                    "evidence": "User-provided launch brief.",
                                    "confidence": "medium",
                                    "usage": "Supports decision framing.",
                                }
                            ],
                            "data_to_extract": [],
                            "content_gaps": [],
                            "accepted_assumptions": [],
                            "status": "confirmed",
                        }
                    ],
                    "open_questions": [],
                }
            )
            (workspace / "slide_intent_plan.json").write_text(
                json.dumps(slide_intent, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--workspace",
                    str(workspace),
                    "--stage",
                    "slide-intent-lock",
                ],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "PASS")

    def test_visual_contract_requires_native_trace_plan(self) -> None:
        gate_module = load_gate_module()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "slides").mkdir()
            (workspace / "styles").mkdir()
            write_gate_scaffolding(workspace)
            comp = workspace / "slides" / "slide-001-comp.png"
            comp.write_bytes(fake_png())
            (workspace / "slides" / "raw" / "slide-001-imagegen.png").write_bytes(fake_png())
            contact = workspace / "styles" / "option-a-contact-sheet.png"
            contact.write_bytes(fake_png(2400, 1350))
            deck_spec = {
                "deck": {"slide_count": 1},
                "slides": [{"slide_id": "slide-001"}],
            }
            visual_contract = {
                **visual_contract_generation_defaults(),
                "selected_style": "Option A",
                "contact_sheet": "styles/option-a-contact-sheet.png",
                "per_slide_comps_complete": True,
                "image_quality_policy": quality_policy(),
                "slides": [
                    {
                        "slide_id": "slide-001",
                        "comp_path": "slides/slide-001-comp.png",
                        "normalization": normalization_record(1),
                        "image_source_type": "imagegen",
                        "visual_archetype": "system map",
                        "reconstruction_mode": "native_trace_hybrid",
                    }
                ],
            }
            failures: list[str] = []
            gate_module.check_visual_contract(workspace, deck_spec, visual_contract, failures)
            self.assertTrue(any("native_trace_plan" in item for item in failures))
            self.assertTrue(any("editable_overlay_plan" in item for item in failures))
            self.assertTrue(any("clarity_review" in item for item in failures))

            visual_contract["slides"][0].update(
                {
                    "clarity_review": clarity_review(),
                    "style_continuity_review": style_continuity_review(),
                    "native_trace_plan": native_trace_plan(),
                    "comp_backplate": {
                        "strategy": "none",
                        "path": "",
                        "insert_first": False,
                        "covers_full_slide": False,
                    },
                    "text_mask_plan": [
                        {"region": "not applicable", "method": "source image not retained", "reason": "native trace"}
                    ],
                    "editable_overlay_plan": native_overlay_plan(),
                }
            )
            failures = []
            gate_module.check_visual_contract(workspace, deck_spec, visual_contract, failures)
            self.assertEqual(failures, [])

    def test_visual_contract_rejects_blurry_comps(self) -> None:
        gate_module = load_gate_module()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "slides").mkdir()
            (workspace / "styles").mkdir()
            write_gate_scaffolding(workspace)
            (workspace / "slides" / "slide-001-comp.png").write_bytes(fake_png())
            (workspace / "slides" / "raw" / "slide-001-imagegen.png").write_bytes(fake_png())
            (workspace / "styles" / "option-a-contact-sheet.png").write_bytes(fake_png(2400, 1350))
            deck_spec = {
                "deck": {"slide_count": 1},
                "slides": [{"slide_id": "slide-001"}],
            }
            bad_clarity = clarity_review()
            bad_clarity.update(
                {
                    "status": "needs_iteration",
                    "image_dimensions_px": {"width": 1024, "height": 576},
                    "text_legibility": "failed",
                    "icon_line_clarity": "failed",
                    "blocking_blur": True,
                }
            )
            visual_contract = {
                **visual_contract_generation_defaults(),
                "selected_style": "Option A",
                "contact_sheet": "styles/option-a-contact-sheet.png",
                "per_slide_comps_complete": True,
                "image_quality_policy": quality_policy(),
                "slides": [
                    {
                        "slide_id": "slide-001",
                        "comp_path": "slides/slide-001-comp.png",
                        "normalization": normalization_record(1),
                        "image_source_type": "imagegen",
                        "visual_archetype": "system map",
                        "reconstruction_mode": "native_trace_hybrid",
                        "native_trace_plan": native_trace_plan(),
                        "clarity_review": bad_clarity,
                        "style_continuity_review": style_continuity_review(),
                        "comp_backplate": {"strategy": "none", "path": "", "insert_first": False, "covers_full_slide": False},
                        "text_mask_plan": [
                            {"region": "title", "method": "shape mask", "reason": "editable title overlay"}
                        ],
                        "editable_overlay_plan": {
                            "visible_native_text_overlay": True,
                            "visible_overlay_count": 2,
                        },
                    }
                ],
            }
            failures: list[str] = []
            gate_module.check_visual_contract(workspace, deck_spec, visual_contract, failures)
            self.assertTrue(any("clarity_review.status" in item for item in failures))
            self.assertTrue(any("blocking_blur" in item for item in failures))
            self.assertTrue(any("image_dimensions_px" in item for item in failures))

    def test_visual_contract_rejects_html_blueprint_surrogate(self) -> None:
        gate_module = load_gate_module()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "slides").mkdir()
            (workspace / "styles").mkdir()
            write_gate_scaffolding(workspace)
            (workspace / "slides" / "slide-001-comp.png").write_bytes(fake_png())
            (workspace / "slides" / "raw" / "slide-001-imagegen.png").write_bytes(fake_png())
            (workspace / "slides" / "slide-001.html").write_text("<html></html>", encoding="utf-8")
            (workspace / "styles" / "option-a-contact-sheet.png").write_bytes(fake_png(2400, 1350))
            deck_spec = {
                "deck": {"slide_count": 1},
                "slides": [{"slide_id": "slide-001"}],
            }
            visual_contract = {
                **visual_contract_generation_defaults(),
                "selected_style": "Option A",
                "contact_sheet": "styles/option-a-contact-sheet.png",
                "per_slide_comps_complete": True,
                "image_quality_policy": quality_policy(),
                "slides": [
                    {
                        "slide_id": "slide-001",
                        "comp_path": "slides/slide-001-comp.png",
                        "normalization": normalization_record(1),
                        "image_source_type": "imagegen",
                        "visual_archetype": "system map",
                        "reconstruction_mode": "native_trace_hybrid",
                        "native_trace_plan": native_trace_plan(),
                        "clarity_review": clarity_review(),
                        "style_continuity_review": style_continuity_review(),
                        "comp_backplate": {"strategy": "none", "path": "", "insert_first": False, "covers_full_slide": False},
                        "text_mask_plan": [
                            {"region": "title", "method": "shape mask", "reason": "editable title overlay"}
                        ],
                        "editable_overlay_plan": {
                            "visible_native_text_overlay": True,
                            "visible_overlay_count": 2,
                        },
                    }
                ],
            }
            failures: list[str] = []
            gate_module.check_visual_contract(workspace, deck_spec, visual_contract, failures)
            self.assertTrue(any("HTML/CSS/browser surrogate" in item for item in failures))
            self.assertTrue(any("HTML/browser blueprint" in item for item in failures))

    def test_visual_contract_rejects_mixed_comp_dimensions(self) -> None:
        gate_module = load_gate_module()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "slides").mkdir()
            (workspace / "styles").mkdir()
            write_gate_scaffolding(workspace)
            (workspace / "slides" / "slide-001-comp.png").write_bytes(fake_png(3840, 2160))
            (workspace / "slides" / "slide-002-comp.png").write_bytes(fake_png(1920, 1080))
            (workspace / "slides" / "raw" / "slide-001-imagegen.png").write_bytes(fake_png(3840, 2160))
            (workspace / "slides" / "raw" / "slide-002-imagegen.png").write_bytes(fake_png(1920, 1080))
            (workspace / "styles" / "option-a-contact-sheet.png").write_bytes(fake_png(2400, 1350))
            deck_spec = {
                "deck": {"slide_count": 2},
                "slides": [{"slide_id": "slide-001"}, {"slide_id": "slide-002"}],
            }
            visual_contract = {
                **visual_contract_generation_defaults(),
                "selected_style": "Option A",
                "contact_sheet": "styles/option-a-contact-sheet.png",
                "per_slide_comps_complete": True,
                "image_quality_policy": quality_policy(),
                "slides": [],
            }
            for idx in (1, 2):
                review = clarity_review()
                if idx == 2:
                    review["image_dimensions_px"] = {"width": 1920, "height": 1080}
                visual_contract["slides"].append(
                    {
                        "slide_id": f"slide-{idx:03d}",
                        "comp_path": f"slides/slide-{idx:03d}-comp.png",
                        "normalization": normalization_record(idx),
                        "image_source_type": "imagegen",
                        "visual_archetype": "system map",
                        "reconstruction_mode": "native_trace_hybrid",
                        "native_trace_plan": native_trace_plan(),
                        "clarity_review": review,
                        "style_continuity_review": style_continuity_review(),
                        "comp_backplate": {
                            "strategy": "none",
                            "path": "",
                            "insert_first": False,
                            "covers_full_slide": False,
                        },
                        "text_mask_plan": [
                            {"region": "title", "method": "shape mask", "reason": "editable title overlay"}
                        ],
                        "editable_overlay_plan": {
                            "visible_native_text_overlay": True,
                            "visible_overlay_count": 2,
                        },
                    }
                )
            failures: list[str] = []
            gate_module.check_visual_contract(workspace, deck_spec, visual_contract, failures)
            self.assertTrue(any("dimensions must match every other slide" in item for item in failures))
            self.assertTrue(any("approved comp file must be at least 3840x2160" in item for item in failures))

    def test_visual_contract_rejects_parallel_page_subagent_generation_without_user_acceptance(self) -> None:
        gate_module = load_gate_module()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "slides").mkdir()
            (workspace / "styles").mkdir()
            write_gate_scaffolding(workspace)
            (workspace / "slides" / "slide-001-comp.png").write_bytes(fake_png())
            (workspace / "slides" / "raw" / "slide-001-imagegen.png").write_bytes(fake_png())
            (workspace / "styles" / "option-a-contact-sheet.png").write_bytes(fake_png(2400, 1350))
            deck_spec = {
                "deck": {"slide_count": 1},
                "slides": [{"slide_id": "slide-001"}],
            }
            visual_contract = {
                **visual_contract_generation_defaults(),
                "selected_style": "Option A",
                "contact_sheet": "styles/option-a-contact-sheet.png",
                "per_slide_comps_complete": True,
                "comp_generation_mode": "parallel_page_subagents",
                "parallel_page_subagents_used": True,
                "explicit_parallel_comp_generation_accepted": False,
                "comp_style_lock": {
                    **visual_contract_generation_defaults()["comp_style_lock"],
                    "generation_owner": "page_subagents",
                },
                "image_quality_policy": quality_policy(),
                "slides": [
                    {
                        "slide_id": "slide-001",
                        "comp_path": "slides/slide-001-comp.png",
                        "normalization": normalization_record(1),
                        "image_source_type": "imagegen",
                        "visual_archetype": "system map",
                        "reconstruction_mode": "native_trace_hybrid",
                        "native_trace_plan": native_trace_plan(),
                        "clarity_review": clarity_review(),
                        "style_continuity_review": style_continuity_review(),
                        "comp_backplate": {"strategy": "none", "path": "", "insert_first": False, "covers_full_slide": False},
                        "text_mask_plan": [
                            {"region": "title", "method": "shape mask", "reason": "editable title overlay"}
                        ],
                        "editable_overlay_plan": {
                            "visible_native_text_overlay": True,
                            "visible_overlay_count": 2,
                        },
                    }
                ],
            }
            failures: list[str] = []
            gate_module.check_visual_contract(workspace, deck_spec, visual_contract, failures)
            self.assertTrue(any("comp_generation_mode" in item for item in failures))
            self.assertTrue(any("parallel_page_subagents_used" in item for item in failures))
            self.assertTrue(any("generation_owner" in item for item in failures))

    def test_visual_contract_allows_style_sharded_serial_generation(self) -> None:
        gate_module = load_gate_module()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "slides" / "style-lane-A").mkdir(parents=True)
            (workspace / "slides" / "raw" / "style-lane-A").mkdir(parents=True)
            (workspace / "styles").mkdir()
            write_gate_scaffolding(workspace)
            (workspace / "slides" / "style-lane-A" / "slide-001-comp.png").write_bytes(fake_png())
            (workspace / "slides" / "raw" / "style-lane-A" / "slide-001-imagegen.png").write_bytes(fake_png())
            (workspace / "styles" / "option-a-contact-sheet.png").write_bytes(fake_png(2400, 1350))
            deck_spec = {
                "deck": {"slide_count": 1},
                "slides": [{"slide_id": "slide-001"}],
            }
            normalization = normalization_record(1)
            normalization.update(
                {
                    "raw_imagegen_output_path": "slides/raw/style-lane-A/slide-001-imagegen.png",
                    "output_path": "slides/style-lane-A/slide-001-comp.png",
                }
            )
            visual_contract = {
                **visual_contract_generation_defaults(),
                "selected_style": "Option A",
                "selected_styles": ["Option A"],
                "contact_sheet": "styles/option-a-contact-sheet.png",
                "per_slide_comps_complete": True,
                "comp_generation_mode": "style_sharded_serial_imagegen",
                "parallel_style_agents_used": True,
                "parallel_page_subagents_used": False,
                "comp_style_lock": {
                    **visual_contract_generation_defaults()["comp_style_lock"],
                    "generation_owner": "style_agent",
                },
                "style_runs": [
                    {
                        "style_lane_id": "style-lane-A",
                        "option_id": "A",
                        "selected_for_pptx": True,
                        "per_slide_comps_complete": True,
                        "normalized_4k_complete": True,
                    }
                ],
                "image_quality_policy": quality_policy(),
                "slides": [
                    {
                        "slide_id": "slide-001",
                        "comp_path": "slides/style-lane-A/slide-001-comp.png",
                        "normalization": normalization,
                        "image_source_type": "imagegen",
                        "visual_archetype": "system map",
                        "reconstruction_mode": "native_trace_hybrid",
                        "native_trace_plan": native_trace_plan(),
                        "clarity_review": clarity_review(),
                        "style_continuity_review": style_continuity_review(),
                        "comp_backplate": {"strategy": "none", "path": "", "insert_first": False, "covers_full_slide": False},
                        "text_mask_plan": [
                            {"region": "title", "method": "shape mask", "reason": "editable title overlay"}
                        ],
                        "editable_overlay_plan": {
                            "visible_native_text_overlay": True,
                            "visible_overlay_count": 2,
                        },
                    }
                ],
            }
            failures: list[str] = []
            gate_module.check_visual_contract(workspace, deck_spec, visual_contract, failures)
            self.assertEqual(failures, [])

    def test_style_gate_rejects_content_strategy_as_visual_style(self) -> None:
        gate_module = load_gate_module()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "styles" / "prompts").mkdir(parents=True)
            (workspace / "styles" / "prompts" / "option-A.txt").write_text("prompt", encoding="utf-8")
            (workspace / "styles" / "option-A-contact-sheet.png").write_bytes(fake_png(2400, 1350))
            deck_spec = {
                "deck": {"deck_profile": "internal-review", "slide_count": 1},
                "slides": [
                    {
                        "slide_id": "slide-001",
                        "title": "Title",
                        "claim": "Claim",
                        "proof_object": "loop",
                    }
                ],
            }
            fingerprint = gate_module.deck_spec_fingerprint(deck_spec)
            slide_intent_plan = {"lock_state": "locked"}
            narrative_plan = {"selected_narrative_id": "narrative-a"}
            design_system = {"taste_guidance": taste_guidance()}
            invariance = {
                "slide_count_ok": True,
                "order_ok": True,
                "claims_preserved": True,
                "data_sources_preserved": True,
                "proof_object_intent_preserved": True,
                "selected_narrative_preserved": True,
                "violations": [],
            }
            style_brief = {
                "direction_count": 1,
                "user_requested_count": 1,
                "selection_mode": "ask_user",
                "generation_mode": "parallel_style_lanes",
                "deck_profile": "internal-review",
                "style_variation_scope": "visual_aesthetic_only",
                "content_strategy_locked": True,
                "style_library": style_library(),
                "taste_guidance": taste_guidance(),
                "image_quality_policy": quality_policy(),
                "imagegen_failure_policy": failure_policy(),
                "imagegen_retry_log": "imagegen_retry_log.json",
                "selected_option": "A",
                "selected_narrative_id": "narrative-a",
                "narrative_lock": {
                    "deck_spec_fingerprint": fingerprint,
                    "locked_slide_count": 1,
                    "locked_slide_order": ["slide-001"],
                    "slide_intent_plan": "slide_intent_plan.json",
                    "slide_intent_lock_state": "locked",
                    "narrative_plan": "narrative_plan.json",
                    "narrative_plan_lock_state": "locked",
                    "slide_order_locked": True,
                    "section_flow_locked": True,
                    "titles_locked": True,
                    "claims_locked": True,
                    "required_data_locked": True,
                    "core_proof_objects_locked": True,
                },
                "candidate_directions": [
                    {
                        "option_id": "A",
                        "style_id": "mckinsey-consulting-report",
                        "style_source": "built-in-style-library",
                        "style_lane_id": "risk-system-map",
                        "aesthetic_family": "data-command-center",
                        "name": "经营驾驶舱",
                        "premise": "以风险系统图重写页面表达",
                        "visual_signature": "white consulting grid with crisp evidence charts",
                        "style_variation_scope": "visual_aesthetic_only",
                        "narrative_behavior": "same_story_reexpressed",
                    }
                ],
                "style_lanes": [
                    {
                        "option_id": "A",
                        "style_id": "mckinsey-consulting-report",
                        "style_source": "built-in-style-library",
                        "style_lane_id": "risk-system-map",
                        "aesthetic_family": "data-command-center",
                        "name": "经营驾驶舱",
                        "visual_signature": "white consulting grid with crisp evidence charts",
                        "generator": "imagegen",
                        "status": "selected",
                        "prompt_path": "styles/prompts/option-A.txt",
                        "output_path": "styles/option-A-contact-sheet.png",
                        "narrative_lock_ref": fingerprint,
                        "invariance_check": invariance,
                    }
                ],
                "style_contact_sheets": [
                    {
                        "option_id": "A",
                        "style_id": "mckinsey-consulting-report",
                        "style_source": "built-in-style-library",
                        "style_lane_id": "risk-system-map",
                        "aesthetic_family": "data-command-center",
                        "name": "经营驾驶舱",
                        "visual_signature": "white consulting grid with crisp evidence charts",
                        "style_variation_scope": "visual_aesthetic_only",
                        "generator": "imagegen",
                        "path": "styles/option-A-contact-sheet.png",
                        "prompt_path": "styles/prompts/option-A.txt",
                        "narrative_lock_ref": fingerprint,
                        "invariance_check": invariance,
                    }
                ],
            }
            (workspace / "imagegen_retry_log.json").write_text(
                json.dumps({"policy_ref": "style_brief.json.imagegen_failure_policy", "attempts": []}) + "\n",
                encoding="utf-8",
            )
            failures: list[str] = []
            gate_module.check_style_gate(
                workspace,
                deck_spec,
                slide_intent_plan,
                narrative_plan,
                design_system,
                style_brief,
                failures,
            )
            self.assertTrue(any("content/narrative term" in item for item in failures))
            self.assertTrue(any("style label" in item for item in failures))

    def test_style_gate_rejects_imagegen_retry_downgrade(self) -> None:
        gate_module = load_gate_module()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "styles" / "prompts").mkdir(parents=True)
            (workspace / "styles" / "prompts" / "option-A.txt").write_text("original prompt", encoding="utf-8")
            (workspace / "styles" / "prompts" / "option-A-retry-01.txt").write_text("retry prompt", encoding="utf-8")
            (workspace / "styles" / "option-A-contact-sheet.png").write_bytes(fake_png(2400, 1350))
            deck_spec = {
                "deck": {"deck_profile": "internal-review", "slide_count": 1},
                "slides": [{"slide_id": "slide-001", "title": "Title", "claim": "Claim"}],
            }
            fingerprint = gate_module.deck_spec_fingerprint(deck_spec)
            invariance = {
                "slide_count_ok": True,
                "order_ok": True,
                "claims_preserved": True,
                "data_sources_preserved": True,
                "proof_object_intent_preserved": True,
                "selected_narrative_preserved": True,
                "violations": [],
            }
            style_brief = {
                "direction_count": 1,
                "user_requested_count": 1,
                "selection_mode": "ask_user",
                "generation_mode": "parallel_style_lanes",
                "deck_profile": "internal-review",
                "style_variation_scope": "visual_aesthetic_only",
                "content_strategy_locked": True,
                "style_library": style_library(),
                "taste_guidance": taste_guidance(),
                "image_quality_policy": quality_policy(),
                "imagegen_failure_policy": failure_policy(),
                "imagegen_retry_log": "imagegen_retry_log.json",
                "selected_option": "A",
                "selected_narrative_id": "narrative-a",
                "narrative_lock": {
                    "deck_spec_fingerprint": fingerprint,
                    "locked_slide_count": 1,
                    "locked_slide_order": ["slide-001"],
                    "slide_intent_plan": "slide_intent_plan.json",
                    "slide_intent_lock_state": "locked",
                    "narrative_plan": "narrative_plan.json",
                    "narrative_plan_lock_state": "locked",
                    "slide_order_locked": True,
                    "section_flow_locked": True,
                    "titles_locked": True,
                    "claims_locked": True,
                    "required_data_locked": True,
                    "core_proof_objects_locked": True,
                },
                "candidate_directions": [
                    {
                        "option_id": "A",
                        "style_id": "swiss-international",
                        "style_source": "built-in-style-library",
                        "style_lane_id": "style-lane-A",
                        "aesthetic_family": "editorial-gallery",
                        "style_variation_scope": "visual_aesthetic_only",
                        "name": "Swiss international",
                        "premise": "Precise grid, limited color, exact spacing",
                        "visual_signature": "Swiss grid, exact spacing, limited color, strong alignment",
                        "narrative_behavior": "same_story_reexpressed",
                    }
                ],
                "style_lanes": [
                    {
                        "option_id": "A",
                        "style_id": "swiss-international",
                        "style_source": "built-in-style-library",
                        "style_lane_id": "style-lane-A",
                        "aesthetic_family": "editorial-gallery",
                        "visual_signature": "Swiss grid, exact spacing, limited color, strong alignment",
                        "generator": "imagegen",
                        "status": "selected",
                        "prompt_path": "styles/prompts/option-A.txt",
                        "output_path": "styles/option-A-contact-sheet.png",
                        "narrative_lock_ref": fingerprint,
                        "invariance_check": invariance,
                    }
                ],
                "style_contact_sheets": [
                    {
                        "option_id": "A",
                        "style_id": "swiss-international",
                        "style_source": "built-in-style-library",
                        "style_lane_id": "style-lane-A",
                        "aesthetic_family": "editorial-gallery",
                        "visual_signature": "Swiss grid, exact spacing, limited color, strong alignment",
                        "style_variation_scope": "visual_aesthetic_only",
                        "generator": "imagegen",
                        "path": "styles/option-A-contact-sheet.png",
                        "prompt_path": "styles/prompts/option-A.txt",
                        "narrative_lock_ref": fingerprint,
                        "invariance_check": invariance,
                    }
                ],
            }
            retry_log = {
                "policy_ref": "style_brief.json.imagegen_failure_policy",
                "attempts": [
                    {
                        "asset_id": "style-lane-A",
                        "stage": "style-contact-sheet",
                        "attempt_index": 1,
                        "failure_class": "server_error",
                        "original_prompt_path": "styles/prompts/option-A.txt",
                        "retry_prompt_path": "styles/prompts/option-A-retry-01.txt",
                        "compression_strategy": "only kept template frame and six titles",
                        "compression_preserved": {
                            "locked_slide_order": True,
                            "slide_titles": True,
                            "core_claims": False,
                            "required_data": False,
                            "proof_object_intent": False,
                            "template_constraints": True,
                            "visual_density_floor": False,
                            "aesthetic_family": True,
                        },
                        "removed_locked_content": True,
                        "reduced_content_density": True,
                        "reduced_visual_density": True,
                        "used_html_surrogate": True,
                        "switched_to_generic_ppt": True,
                        "next_action": "blocked_ask_user",
                        "final_status": "blocked_imagegen_failure",
                    }
                ],
            }
            (workspace / "imagegen_retry_log.json").write_text(
                json.dumps(retry_log, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            failures: list[str] = []
            gate_module.check_style_gate(
                workspace,
                deck_spec,
                {"lock_state": "locked"},
                {"selected_narrative_id": "narrative-a"},
                {"taste_guidance": taste_guidance()},
                style_brief,
                failures,
            )
            self.assertTrue(any("forbidden downgrade flag" in item for item in failures))
            self.assertTrue(any("compression_preserved.core_claims" in item for item in failures))
            self.assertTrue(any("unresolved but it is marked ready/selected" in item for item in failures))

    def test_reconstruction_only_before_pptx_skips_full_pipeline_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_json(
                [
                    sys.executable,
                    str(INIT_SCRIPT),
                    "--slug",
                    "reconstruct-pass",
                    "--title",
                    "Reconstruct Pass",
                    "--mode",
                    "reconstruction-only",
                    "--root",
                    tmp,
                ]
            )
            workspace = Path(result["workspace"])
            (workspace / "slides" / "slide-001-comp.png").write_bytes(fake_png())

            pipeline_state = json.loads((workspace / "pipeline_state.json").read_text(encoding="utf-8"))
            pipeline_state["current_stage"] = "visual_contract"
            pipeline_state["stage_history"].extend(
                [
                    {"stage": "reconstruction_input_lock", "status": "completed", "timestamp": "test", "notes": ""},
                    {"stage": "visual_contract", "status": "completed", "timestamp": "test", "notes": ""},
                ]
            )
            (workspace / "pipeline_state.json").write_text(
                json.dumps(pipeline_state, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            deck_spec = json.loads((workspace / "deck_spec.json").read_text(encoding="utf-8"))
            deck_spec["deck"].update({"slide_count": 1, "lock_state": "locked"})
            deck_spec["slides"] = [{"slide_id": "slide-001", "page_number": 1, "title": "Editable title"}]
            (workspace / "deck_spec.json").write_text(
                json.dumps(deck_spec, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            manifest = json.loads((workspace / "reconstruction_manifest.json").read_text(encoding="utf-8"))
            manifest.update(
                {
                    "lock_state": "locked",
                    "slide_count": 1,
                    "slides": [
                        {
                            "slide_id": "slide-001",
                            "page_number": 1,
                            "source_image_path": "slides/slide-001-comp.png",
                            "text_source_status": "provided",
                            "text_source_path": "",
                            "reconstruction_mode": "native_trace_hybrid",
                            "native_trace_plan": native_trace_plan(),
                            "required_editable_overlays": ["title"],
                            "editable_overlay_coverage": {
                                "visible_native_text_overlay": True,
                                "visible_overlay_count": 4,
                            },
                            "output_slide_pptx": "slide-modules/slide-001.pptx",
                            "preview_path": "preview/slide-001-pptx.png",
                            "review_status": "not_started",
                        }
                    ],
                }
            )
            (workspace / "reconstruction_manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            visual_contract = json.loads((workspace / "visual_contract.json").read_text(encoding="utf-8"))
            visual_contract.update(
                {
                    "selected_style": "user-supplied-final-images",
                    "per_slide_comps_complete": True,
                    "image_quality_policy": quality_policy(),
                    "slides": [
                        {
                            "slide_id": "slide-001",
                            "comp_path": "slides/slide-001-comp.png",
                            "visual_archetype": "source image",
                            "reconstruction_mode": "native_trace_hybrid",
                            "native_trace_plan": native_trace_plan(),
                            "clarity_review": clarity_review(),
                            "comp_backplate": {
                                "strategy": "none",
                                "path": "",
                                "insert_first": False,
                                "covers_full_slide": False,
                            },
                            "text_mask_plan": [
                                {"region": "not applicable", "method": "source image not retained", "reason": "native trace"}
                            ],
                            "editable_overlay_plan": native_overlay_plan(),
                        }
                    ],
                }
            )
            (workspace / "visual_contract.json").write_text(
                json.dumps(visual_contract, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--workspace",
                    str(workspace),
                    "--stage",
                    "before-pptx",
                ],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
