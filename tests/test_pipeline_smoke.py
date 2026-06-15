from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image
from pptx.dml.color import RGBColor


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "imagegen-pptx-pipeline"
INIT_SCRIPT = SKILL_DIR / "scripts" / "init_pipeline_workspace.py"
GATE_SCRIPT = SKILL_DIR / "scripts" / "check_pipeline_gates.py"
SLIDELIB = SKILL_DIR / "slidelib.py"
ICONCUT = SKILL_DIR / "iconcut3.py"
QAGATE = SKILL_DIR / "qa_gate.py"
SLIDE_COMP_REVIEW_ROLES = [
    "content-integrity",
    "text-typography",
    "visual-fidelity",
    "style-continuity",
    "image-art-director",
    "layout-pptx-feasibility",
    "chart-logic",
    "asset-authenticity",
    "template-fidelity",
    "accessibility-readability",
    "visual-clarity",
]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def run_json(args: list[str], *, check: bool = True) -> dict:
    completed = subprocess.run(args, check=check, text=True, capture_output=True)
    return json.loads(completed.stdout)


def write_noise_png(path: Path, width: int = 1920, height: int = 1080) -> None:
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 255, (height, width, 3), dtype=np.uint8)
    Image.fromarray(arr, "RGB").save(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def init_workspace(root: Path, mode: str = "reconstruction-only") -> Path:
    payload = run_json(
        [
            sys.executable,
            str(INIT_SCRIPT),
            "--slug",
            "smoke",
            "--title",
            "Smoke",
            "--mode",
            mode,
            "--root",
            str(root),
        ]
    )
    return Path(payload["workspace"])


def lock_direct_conversion_workspace(workspace: Path, *, final: bool = False) -> None:
    slide_path = workspace / "slides" / "slide-001-comp.png"
    slide_path.parent.mkdir(parents=True, exist_ok=True)
    write_noise_png(slide_path)

    deck_spec = json.loads((workspace / "deck_spec.json").read_text(encoding="utf-8"))
    deck_spec["deck"].update(
        {
            "deck_profile": "internal-review",
            "content_input_type": "final_slide_images",
            "slide_count": 1,
            "lock_state": "locked",
        }
    )
    deck_spec["slides"] = [
        {
            "slide_id": "slide-001",
            "page_number": 1,
            "title": "Smoke",
            "claim": "The converter can build an editable slide.",
            "body_text": ["Native text"],
            "proof_object": "diagram",
            "visual_intent": "Simple smoke layout",
            "editable_text": ["title", "body_text"],
        }
    ]
    (workspace / "deck_spec.json").write_text(json.dumps(deck_spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    state = json.loads((workspace / "pipeline_state.json").read_text(encoding="utf-8"))
    state["current_stage"] = "visual_contract" if not final else "final_review"
    state["stage_history"] = [
        {"stage": "initialized", "status": "completed", "timestamp": "test", "notes": ""},
        {"stage": "conversion_input_lock", "status": "completed", "timestamp": "test", "notes": ""},
        {"stage": "visual_contract", "status": "completed", "timestamp": "test", "notes": ""},
    ]
    if final:
        state["stage_history"].append({"stage": "pptx_conversion", "status": "completed", "timestamp": "test", "notes": ""})
    (workspace / "pipeline_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    visual_contract = json.loads((workspace / "visual_contract.json").read_text(encoding="utf-8"))
    visual_contract.update(
        {
            "selected_style": "user-supplied-final-images",
            "selected_styles": ["user-supplied-final-images"],
            "per_slide_comps_complete": True,
            "conversion_method": "strict_slide_image_to_editable_pptx",
            "comp_is_conversion_target": True,
            "slides": [
                {
                    "slide_id": "slide-001",
                    "comp_path": "slides/slide-001-comp.png",
                    "image_source_type": "user_supplied",
                    "visual_archetype": "diagram",
                    "clarity_review": {
                        "status": "approved",
                        "blocking_blur": False,
                        "image_dimensions_px": {"width": 1920, "height": 1080},
                        "image_file_size_bytes": slide_path.stat().st_size,
                    },
                    "converter": {
                        "measurement_status": "approved" if final else "planned",
                        "text_split_plan": "completed" if final else "planned",
                        "build_script_path": "builders/slide-001.py",
                        "output_slide_pptx": "slide-modules/slide-001.pptx",
                        "preview_path": "preview/slide-001-render.png",
                    },
                }
            ],
        }
    )
    (workspace / "visual_contract.json").write_text(
        json.dumps(visual_contract, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = json.loads((workspace / "conversion_manifest.json").read_text(encoding="utf-8"))
    manifest.update({"lock_state": "locked", "slide_count": 1})
    manifest["slides"] = [
        {
            "slide_id": "slide-001",
            "source_image_path": "slides/slide-001-comp.png",
            "basis_image_path": "measurements/slide-001-src.png",
            "text_source_status": "provided",
            "measurement_status": "approved" if final else "planned",
            "icon_extraction_status": "not_applicable",
            "icon_edge_audit_status": "not_applicable",
            "icon_contact_sheet_audit_status": "not_applicable",
            "source_icon_inventory_status": "no_source_icons_detected",
            "extracted_icon_count": 0,
            "build_script_path": "builders/slide-001.py",
            "output_slide_pptx": "slide-modules/slide-001.pptx",
            "preview_path": "preview/slide-001-render.png",
            "latest_render_path": "preview/slide-001-render.png",
            "render_log_path": "qa/render-compare/render_log.json",
            "native_build_status": "approved" if final else "planned",
            "render_compare_rounds_completed": 10 if final else 0,
            "paired_crops_status": "passed" if final else "pending",
            "max_region_mean_abs": 0.0 if final else 0,
            "actual_max_region_mean_abs": 0.0 if final else 0,
            "review_status": "approved" if final else "not_started",
        }
    ]

    if final:
        (workspace / "builders").mkdir(exist_ok=True)
        (workspace / "builders" / "slide-001.py").write_text("# smoke\n", encoding="utf-8")
        (workspace / "slide-modules").mkdir(exist_ok=True)
        slidelib = load_module(SLIDELIB, "slidelib_final_smoke")
        module_pptx = workspace / "slide-modules" / "slide-001.pptx"
        deck = slidelib.SB(1920, 1080, slidelib.WHITE)
        for idx in range(10):
            deck.text(80, 80 + idx * 42, 500, 30, f"Native text run {idx}", size=18, color=slidelib.DARK)
        deck.save(module_pptx)
        (workspace / "preview").mkdir(exist_ok=True)
        source_render = Image.open(slide_path).convert("RGB")
        for idx in range(1, 11):
            source_render.save(workspace / "preview" / f"r-{idx}.png")
        source_render.save(workspace / "preview" / "slide-001-render.png")
        (workspace / "output").mkdir(exist_ok=True)
        output = workspace / "output" / "smoke.pptx"
        output.write_bytes(module_pptx.read_bytes())
        manifest["final_outputs"] = [{"path": "output/smoke.pptx", "sha256": sha256(output)}]
        rounds = {
            "status": "passed",
            "policy_ref": "visual_contract.json.render_compare_loop",
            "minimum_rounds": 10,
            "completed_rounds": 10,
            "rounds": [{"round": idx, "pptx": "slide-modules/slide-001.pptx", "render": f"preview/r-{idx}.png", "fixes": [], "unresolved": []} for idx in range(1, 11)],
            "paired_crops": [{"slide_id": "slide-001", "source_crop": "crops/src-title.png", "render_crop": "crops/render-title.png", "status": "passed"}],
            "region_metrics": [{"slide_id": "slide-001", "region": "title", "mean_abs": 0.0, "status": "normal"}],
            "unresolved_p0_p1": [],
        }
        render_log = [
            {
                "round": idx,
                "render": f"preview/r-{idx}.png",
                "timestamp": "test",
                "max_metric": 0.0,
                "issues": "none",
                "fix": "none",
                "recheck": "passed",
            }
            for idx in range(1, 11)
        ]
        (workspace / "qa" / "render-compare").mkdir(parents=True, exist_ok=True)
        (workspace / "qa" / "render-compare" / "render_compare_rounds.json").write_text(
            json.dumps(rounds, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (workspace / "qa" / "render-compare" / "render_log.json").write_text(
            json.dumps(render_log, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (workspace / "qa" / "final-council.md").write_text(
            "# Final Deck Council\n\npptx-conversion-fidelity\n\ntaste-direction\n\nnarrative-invariance\n\n## Export Decision\nEXPORT\n",
            encoding="utf-8",
        )
        (workspace / "qa_report.md").write_text(
            "# QA Report\n\n## Status\nPASS\n\n## PPTX Conversion Gate\nPassed.\n\n## Final Council\nExport.\n",
            encoding="utf-8",
        )

    (workspace / "conversion_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def lock_generated_comp_workspace(workspace: Path) -> None:
    slide_path = workspace / "slides" / "slide-001-comp.png"
    sheet_path = workspace / "styles" / "lane-a-contact-sheet.png"
    slide_path.parent.mkdir(parents=True, exist_ok=True)
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    write_noise_png(slide_path)
    write_noise_png(sheet_path, width=2400, height=1350)

    deck_spec = json.loads((workspace / "deck_spec.json").read_text(encoding="utf-8"))
    deck_spec["deck"].update(
        {
            "deck_profile": "internal-review",
            "content_input_type": "explicit_per_page",
            "slide_count": 1,
            "lock_state": "locked",
        }
    )
    deck_spec["slides"] = [
        {
            "slide_id": "slide-001",
            "page_number": 1,
            "title": "Generated Smoke",
            "claim": "Generated comps require role review evidence.",
            "body_text": ["Native text"],
            "proof_object": "diagram",
            "visual_intent": "Simple smoke layout",
            "visual_comp_required": True,
            "comp_path": "slides/slide-001-comp.png",
            "comp_review_status": "approved",
            "editable_text": ["title", "body_text"],
        }
    ]
    (workspace / "deck_spec.json").write_text(json.dumps(deck_spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    gate = load_module(GATE_SCRIPT, "gate_fingerprint_smoke")
    fingerprint = gate.deck_spec_fingerprint(deck_spec)

    state = json.loads((workspace / "pipeline_state.json").read_text(encoding="utf-8"))
    state["current_stage"] = "visual_contract"
    state["stage_history"] = [
        {"stage": "initialized", "status": "completed", "timestamp": "test", "notes": ""},
        {"stage": "content_gate", "status": "completed", "timestamp": "test", "notes": ""},
        {"stage": "slide_intent_lock", "status": "completed", "timestamp": "test", "notes": ""},
        {"stage": "narrative_selection", "status": "completed", "timestamp": "test", "notes": ""},
        {"stage": "style_selection", "status": "completed", "timestamp": "test", "notes": ""},
        {"stage": "single_slide_comps", "status": "completed", "timestamp": "test", "notes": ""},
        {"stage": "slide_comp_review", "status": "completed", "timestamp": "test", "notes": ""},
        {"stage": "visual_contract", "status": "completed", "timestamp": "test", "notes": ""},
    ]
    (workspace / "pipeline_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (workspace / "slide_intent_matrix.md").write_text("# Slide Intent Matrix\n", encoding="utf-8")
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
                    "confirmed_title": "Generated Smoke",
                    "core_idea": "Generated comps require review.",
                    "proof_goal": "Show gate enforcement.",
                    "status": "confirmed",
                }
            ],
            "open_questions": [],
        }
    )
    (workspace / "slide_intent_plan.json").write_text(json.dumps(slide_intent, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (workspace / "narrative_matrix.md").write_text("# Narrative Matrix\n", encoding="utf-8")
    narrative = json.loads((workspace / "narrative_plan.json").read_text(encoding="utf-8"))
    narrative.update(
        {
            "lock_state": "locked",
            "source_deck_spec_fingerprint": fingerprint,
            "slide_intent_lock_state": "locked",
            "selected_narrative_id": "evidence-first",
            "review_status": "approved",
            "slides": [
                {
                    "slide_id": "slide-001",
                    "page_number": 1,
                    "selected_treatment": {
                        "narrative_id": "evidence-first",
                        "presentation_strategy": "Lead with gate behavior.",
                        "content_to_show": "One diagram.",
                        "proof_object_expression": "Diagram",
                        "must_preserve": "Single-slide claim",
                    },
                }
            ],
            "open_questions": [],
        }
    )
    (workspace / "narrative_plan.json").write_text(json.dumps(narrative, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    style = json.loads((workspace / "style_brief.json").read_text(encoding="utf-8"))
    style.update(
        {
            "direction_count": 1,
            "selected_narrative_id": "evidence-first",
            "content_strategy_locked": True,
            "selected_option": "option-a",
            "selected_options": ["option-a"],
            "narrative_lock": {
                "deck_spec_fingerprint": fingerprint,
                "locked_slide_count": 1,
                "locked_slide_order": ["slide-001"],
                "slide_intent_lock_state": "locked",
                "narrative_plan_lock_state": "locked",
            },
            "candidate_directions": [
                {
                    "option_id": "option-a",
                    "style_lane_id": "lane-a",
                    "style_id": "mckinsey-consulting-report",
                    "style_source": "built-in-style-library",
                    "aesthetic_family": "consulting-report",
                    "visual_signature": "crisp consulting system diagram",
                }
            ],
            "style_contact_sheets": [
                {
                    "path": "styles/lane-a-contact-sheet.png",
                    "generator": "imagegen",
                    "style_id": "mckinsey-consulting-report",
                    "style_source": "built-in-style-library",
                    "visual_signature": "crisp consulting system diagram",
                }
            ],
        }
    )
    (workspace / "style_brief.json").write_text(json.dumps(style, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    visual_contract = json.loads((workspace / "visual_contract.json").read_text(encoding="utf-8"))
    visual_contract.update(
        {
            "selected_style": "option-a",
            "selected_styles": ["option-a"],
            "contact_sheet": "styles/lane-a-contact-sheet.png",
            "per_slide_comps_complete": True,
            "conversion_method": "strict_slide_image_to_editable_pptx",
            "comp_is_conversion_target": True,
            "slides": [
                {
                    "slide_id": "slide-001",
                    "comp_path": "slides/slide-001-comp.png",
                    "image_source_type": "imagegen",
                    "visual_archetype": "diagram",
                    "clarity_review": {
                        "status": "approved",
                        "blocking_blur": False,
                        "image_dimensions_px": {"width": 1920, "height": 1080},
                        "image_file_size_bytes": slide_path.stat().st_size,
                    },
                    "style_continuity_review": {"status": "approved"},
                    "converter": {
                        "measurement_status": "planned",
                        "text_split_plan": "planned",
                        "build_script_path": "builders/slide-001.py",
                        "output_slide_pptx": "slide-modules/slide-001.pptx",
                        "preview_path": "preview/slide-001-render.png",
                    },
                }
            ],
        }
    )
    (workspace / "visual_contract.json").write_text(json.dumps(visual_contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = json.loads((workspace / "conversion_manifest.json").read_text(encoding="utf-8"))
    manifest.update({"lock_state": "locked", "slide_count": 1})
    manifest["slides"] = [
        {
            "slide_id": "slide-001",
            "source_image_path": "slides/slide-001-comp.png",
            "basis_image_path": "measurements/slide-001-src.png",
            "text_source_status": "provided",
            "measurement_status": "planned",
            "icon_extraction_status": "not_applicable",
            "icon_edge_audit_status": "not_applicable",
            "icon_contact_sheet_audit_status": "not_applicable",
            "source_icon_inventory_status": "no_source_icons_detected",
            "extracted_icon_count": 0,
            "build_script_path": "builders/slide-001.py",
            "output_slide_pptx": "slide-modules/slide-001.pptx",
            "preview_path": "preview/slide-001-render.png",
            "latest_render_path": "preview/slide-001-render.png",
            "render_log_path": "qa/render-compare/render_log.json",
            "native_build_status": "planned",
            "render_compare_rounds_completed": 0,
            "paired_crops_status": "pending",
            "max_region_mean_abs": 0,
            "review_status": "not_started",
        }
    ]
    (workspace / "conversion_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_slide_comp_review(workspace: Path, *, missing_role: str | None = None) -> None:
    roles = [role for role in SLIDE_COMP_REVIEW_ROLES if role != missing_role]
    review = {
        "review_type": "slide_comp",
        "stage": "slide_comp",
        "slide_id": "slide-001",
        "style_lane_id": "lane-a",
        "approved_comp_path": "slides/slide-001-comp.png",
        "subagent_review_required": True,
        "reviewer_mode": "subagent",
        "required_roles": roles,
        "role_reviews": [
            {
                "role": role,
                "stage": "slide_comp",
                "scope": "slide-001",
                "approval_to_advance": True,
                "findings": [],
                "accepted_risks": [],
                "notes": "approved" if role not in {"chart-logic", "template-fidelity"} else "not applicable for this smoke slide",
            }
            for role in roles
        ],
        "unresolved_p0_p1": [],
        "overall_status": "approved",
        "approval_to_advance": True,
    }
    outdir = workspace / "qa" / "reviews" / "slide-comp"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "slide-001.json").write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class PipelineSmokeTests(unittest.TestCase):
    def test_init_workspace_copies_converter_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(QAGATE.exists())
            workspace = init_workspace(Path(tmp))
            self.assertTrue((workspace / "slidelib.py").exists())
            self.assertTrue((workspace / "iconcut3.py").exists())
            self.assertTrue((workspace / "qa_gate.py").exists())
            self.assertTrue((workspace / "PITFALLS.md").exists())
            self.assertTrue((workspace / "conversion_manifest.json").exists())
            self.assertFalse((workspace / "reconstruction_manifest.json").exists())
            manifest = json.loads((workspace / "conversion_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["conversion_method"], "strict_slide_image_to_editable_pptx")
            self.assertTrue(manifest["global_rules"]["icon_hd_enhancement_required"])
            icon_jobs = json.loads((workspace / "icons" / "icon_jobs.json").read_text(encoding="utf-8"))
            self.assertEqual(icon_jobs["minimum_output_icon_min_dim_px"], 256)
            self.assertEqual(icon_jobs["icon_hd_target_min_px"], 256)

    def test_slidelib_builds_pptx(self) -> None:
        slidelib = load_module(SLIDELIB, "slidelib_smoke")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.pptx"
            slide = slidelib.SB(1920, 1080, slidelib.WHITE)
            slide.rect(120, 120, 400, 180, RGBColor(0xEE, 0xEE, 0xEE), slidelib.LINE_GY)
            slide.text(150, 160, 340, 80, "Native text", size=28, color=slidelib.DARK, bold=True)
            slide.save(output)
            self.assertGreater(output.stat().st_size, 0)

    def test_iconcut_strict_extracts_padded_transparent_icon(self) -> None:
        iconcut = load_module(ICONCUT, "iconcut_smoke")
        with tempfile.TemporaryDirectory() as tmp:
            source = Image.new("RGB", (240, 240), "white")
            for x in range(90, 150):
                for y in range(80, 160):
                    source.putpixel((x, y), (20, 20, 20))
            out = Path(tmp) / "icon.png"
            iconcut.strict_cut3(source, (80, 70, 160, 170), out, scale=1.0, pad=8, min_dim=110, border=10, name="box")
            icon = Image.open(out).convert("RGBA")
            alpha = np.asarray(icon.getchannel("A"))
            self.assertEqual(int(alpha[0, :].max()), 0)
            self.assertEqual(int(alpha[-1, :].max()), 0)
            self.assertEqual(int(alpha[:, 0].max()), 0)
            self.assertEqual(int(alpha[:, -1].max()), 0)

    def test_iconcut_enhance_icon_supersamples_and_keeps_alpha(self) -> None:
        iconcut = load_module(ICONCUT, "iconcut_enhance_smoke")
        source = Image.new("RGBA", (18, 24), (0, 0, 0, 0))
        for x in range(5, 13):
            for y in range(4, 20):
                source.putpixel((x, y), (210, 20, 20, 220))
        enhanced = iconcut.enhance_icon(source, target_min=72, sharpen=True, alpha_crisp=True)
        self.assertGreaterEqual(min(enhanced.size), 72)
        alpha = np.asarray(enhanced.getchannel("A"))
        self.assertGreater(int(alpha.max()), 0)

    def test_iconcut_enhance_dir_preserves_feathered_slice_edges(self) -> None:
        iconcut = load_module(ICONCUT, "iconcut_enhance_dir_smoke")
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp)
            source = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
            for x in range(4, 20):
                for y in range(4, 20):
                    alpha = 220 if 7 <= x <= 16 and 7 <= y <= 16 else 90
                    source.putpixel((x, y), (30, 120, 230, alpha))
            source.save(outdir / "badge.png")
            done = iconcut.enhance_dir(outdir, feathered=("badge",), target_min=64, border=4)
            self.assertEqual(done, [("badge", (72, 72), "feathered")])
            enhanced = Image.open(outdir / "badge.png").convert("RGBA")
            alpha = np.asarray(enhanced.getchannel("A"))
            self.assertEqual(int(alpha[0, :].max()), 0)
            self.assertEqual(int(alpha[-1, :].max()), 0)
            self.assertEqual(int(alpha[:, 0].max()), 0)
            self.assertEqual(int(alpha[:, -1].max()), 0)
            self.assertTrue(bool(((alpha > 0) & (alpha < 255)).any()))

    def test_iconcut_cliperror_fails_closed(self) -> None:
        iconcut = load_module(ICONCUT, "iconcut_clip_smoke")
        source = Image.new("RGB", (80, 80), "white")
        for x in range(0, 20):
            for y in range(0, 20):
                source.putpixel((x, y), (20, 20, 20))
        with self.assertRaises(iconcut.ClipError):
            iconcut.strict_cut3(source, (0, 0, 20, 20), Path(tempfile.gettempdir()) / "bad-icon.png", scale=1.0, pad=0, name="bad")

    def test_before_pptx_gate_accepts_locked_conversion_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = init_workspace(Path(tmp))
            lock_direct_conversion_workspace(workspace)
            payload = run_json([sys.executable, str(GATE_SCRIPT), "--workspace", str(workspace), "--stage", "before-pptx"])
            self.assertEqual(payload["status"], "PASS", payload["failures"])

    def test_generated_before_pptx_gate_requires_slide_comp_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = init_workspace(Path(tmp), mode="create")
            lock_generated_comp_workspace(workspace)
            payload = run_json(
                [sys.executable, str(GATE_SCRIPT), "--workspace", str(workspace), "--stage", "before-pptx"],
                check=False,
            )
            self.assertEqual(payload["status"], "FAIL")
            self.assertTrue(any("missing slide-comp review JSON for slide-001" in item for item in payload["failures"]))

    def test_generated_before_pptx_gate_accepts_slide_comp_review_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = init_workspace(Path(tmp), mode="create")
            lock_generated_comp_workspace(workspace)
            write_slide_comp_review(workspace)
            payload = run_json([sys.executable, str(GATE_SCRIPT), "--workspace", str(workspace), "--stage", "before-pptx"])
            self.assertEqual(payload["status"], "PASS", payload["failures"])

    def test_generated_before_pptx_gate_rejects_incomplete_slide_comp_review_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = init_workspace(Path(tmp), mode="create")
            lock_generated_comp_workspace(workspace)
            write_slide_comp_review(workspace, missing_role="text-typography")
            payload = run_json(
                [sys.executable, str(GATE_SCRIPT), "--workspace", str(workspace), "--stage", "before-pptx"],
                check=False,
            )
            self.assertEqual(payload["status"], "FAIL")
            self.assertTrue(any("text-typography" in item for item in payload["failures"]))

    def test_gate_rejects_icon_not_applicable_without_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = init_workspace(Path(tmp))
            lock_direct_conversion_workspace(workspace)
            manifest_path = workspace / "conversion_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["slides"][0].pop("source_icon_inventory_status", None)
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            payload = run_json(
                [sys.executable, str(GATE_SCRIPT), "--workspace", str(workspace), "--stage", "before-pptx"],
                check=False,
            )
            self.assertEqual(payload["status"], "FAIL")
            self.assertTrue(any("source_icon_inventory_status=no_source_icons_detected" in item for item in payload["failures"]))

    def test_gate_rejects_low_icon_hd_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = init_workspace(Path(tmp))
            lock_direct_conversion_workspace(workspace)
            contract_path = workspace / "visual_contract.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["strict_icon_policy"]["icon_hd_target_min_px"] = 128
            contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            payload = run_json(
                [sys.executable, str(GATE_SCRIPT), "--workspace", str(workspace), "--stage", "before-pptx"],
                check=False,
            )
            self.assertEqual(payload["status"], "FAIL")
            self.assertTrue(any("icon_hd_target_min_px" in item for item in payload["failures"]))

    def test_final_gate_accepts_render_compare_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = init_workspace(Path(tmp))
            lock_direct_conversion_workspace(workspace, final=True)
            payload = run_json([sys.executable, str(GATE_SCRIPT), "--workspace", str(workspace), "--stage", "final"])
            self.assertEqual(payload["status"], "PASS", payload["failures"])

    def test_final_gate_rejects_reused_render_rounds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = init_workspace(Path(tmp))
            lock_direct_conversion_workspace(workspace, final=True)
            log_path = workspace / "qa" / "render-compare" / "render_log.json"
            log = json.loads(log_path.read_text(encoding="utf-8"))
            log[1]["render"] = log[0]["render"]
            log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            payload = run_json([sys.executable, str(GATE_SCRIPT), "--workspace", str(workspace), "--stage", "final"], check=False)
            self.assertEqual(payload["status"], "FAIL")
            self.assertTrue(any("reuses an earlier render" in item for item in payload["failures"]))


if __name__ == "__main__":
    unittest.main()
