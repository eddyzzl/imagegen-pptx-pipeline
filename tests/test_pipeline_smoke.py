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
REALESRGAN_SCRIPT = SKILL_DIR / "scripts" / "realesrgan_upscale.py"
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


def write_noise_png(path: Path, width: int = 3840, height: int = 2160) -> None:
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 255, (height, width, 3), dtype=np.uint8)
    Image.fromarray(arr, "RGB").save(path, format="JPEG", quality=82)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def write_realesrgan_manifest(workspace: Path, source: Path, output: Path, *, kind: str = "comp") -> str:
    model_path = workspace / "assets" / "models" / "RealESRGAN_x4plus.pth"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    if not model_path.exists():
        model_path.write_bytes(b"fake test RealESRGAN_x4plus weights\n")
    if kind == "comp":
        manifest_path = workspace / "upscale" / f"{output.stem}.realesrgan.json"
        target_px = {"width": 3840, "height": 2160}
        target_min = None
    else:
        manifest_path = workspace / "icons" / "icon_upscale_manifest.json"
        target_px = None
        target_min = 256
    with Image.open(source) as im:
        input_size = im.size
    with Image.open(output) as im:
        output_size = im.size
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "processed",
        "tool": "python-realesrganer",
        "engine": "RealESRGANer",
        "backend": "python",
        "generated_at": "test",
        "kind": kind,
        "input": str(source),
        "output": str(output),
        "model": "RealESRGAN_x4plus",
        "model_file": "RealESRGAN_x4plus.pth",
        "model_path": str(model_path),
        "model_sha256": sha256(model_path),
        "device": "cpu",
        "half": False,
        "tile": 400,
        "tile_pad": 12,
        "pre_pad": 0,
        "items": [
            {
                "status": "processed",
                "kind": kind,
                "tool": "python-realesrganer",
                "engine": "RealESRGANer",
                "backend": "python",
                "model": "RealESRGAN_x4plus",
                "model_file": "RealESRGAN_x4plus.pth",
                "model_path": str(model_path),
                "model_sha256": sha256(model_path),
                "device": "cpu",
                "half": False,
                "scale": 4,
                "outscale": 3840 / input_size[0] if kind == "comp" else max(256 / min(input_size), 1.0),
                "tile": 400,
                "tile_pad": 12,
                "pre_pad": 0,
                "input_path": str(source),
                "output_path": str(output),
                "input_sha256": sha256(source),
                "output_sha256": sha256(output),
                "input_px": {"width": input_size[0], "height": input_size[1]},
                "realesrgan_output_px": {"width": output_size[0], "height": output_size[1]},
                "output_px": {"width": output_size[0], "height": output_size[1]},
                "target_px": target_px,
                "target_min_px": target_min,
                "alpha_preserved": kind == "icon",
            }
        ],
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(manifest_path.relative_to(workspace))


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
    raw_path = workspace / "slides" / "raw" / "slide-001-raw.png"
    slide_path = workspace / "slides" / "slide-001-comp.png"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    slide_path.parent.mkdir(parents=True, exist_ok=True)
    write_noise_png(raw_path, width=1920, height=1080)
    write_noise_png(slide_path)
    upscale_manifest = write_realesrgan_manifest(workspace, raw_path, slide_path)

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
                    "raw_comp_path": "slides/raw/slide-001-raw.png",
                    "upscale_manifest_path": upscale_manifest,
                    "image_source_type": "user_supplied",
                    "visual_archetype": "diagram",
                    "clarity_review": {
                        "status": "approved",
                        "blocking_blur": False,
                        "image_dimensions_px": {"width": 3840, "height": 2160},
                        "image_file_size_bytes": slide_path.stat().st_size,
                        "upscale_manifest_path": upscale_manifest,
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
            "raw_source_image_path": "slides/raw/slide-001-raw.png",
            "upscale_manifest_path": upscale_manifest,
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
            "max_region_mean_abs": 5.0 if final else 0,
            "actual_max_region_mean_abs": 5.0 if final else 0,
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
        for idx in range(1, 11):
            (workspace / "preview" / f"r-{idx}.png").write_bytes(slide_path.read_bytes())
        (workspace / "preview" / "slide-001-render.png").write_bytes(slide_path.read_bytes())
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
            "region_metrics": [{"slide_id": "slide-001", "region": "title", "mean_abs": 5.0, "status": "normal"}],
            "unresolved_p0_p1": [],
        }
        render_log = [
            {
                "round": idx,
                "render": f"preview/r-{idx}.png",
                "timestamp": "test",
                "max_metric": 5.0,
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
    raw_path = workspace / "slides" / "raw" / "slide-001-raw.png"
    slide_path = workspace / "slides" / "slide-001-comp.png"
    sheet_path = workspace / "styles" / "lane-a-contact-sheet.png"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    slide_path.parent.mkdir(parents=True, exist_ok=True)
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    write_noise_png(raw_path, width=1920, height=1080)
    write_noise_png(slide_path)
    write_noise_png(sheet_path, width=2400, height=1350)
    upscale_manifest = write_realesrgan_manifest(workspace, raw_path, slide_path)

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
            "deck_profile": "internal-review",
            "deck_profile_evidence": {
                "primary_profile": "internal-review",
                "secondary_profiles": [],
                "audience": "internal reviewers",
                "occasion": "generated comp smoke test",
                "source_signals": ["deck_spec.deck.deck_profile", "slide claim", "proof object"],
                "excluded_style_families": [],
                "notes": "Smoke fixture uses one task-appropriate style lane.",
            },
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
                    "task_fit": {
                        "profile_match": True,
                        "fit_reason": "Internal review smoke deck needs a simple evidence-first system diagram.",
                        "profile_signals_used": ["internal-review", "proof object: diagram"],
                    },
                    "layout_archetype": "single system diagram",
                    "evidence_presentation": "one proof object with supporting label",
                    "composition_grammar": "center-left diagram with sparse annotations",
                    "density_and_pacing": "low-density single-slide smoke fixture",
                    "thumbnail_differentiators": ["crisp diagram", "sparse evidence label"],
                    "must_not_reuse": "Do not collapse into equal-card grid or icon-only variation.",
                }
            ],
            "style_contact_sheets": [
                {
                    "path": "styles/lane-a-contact-sheet.png",
                    "generator": "imagegen",
                    "style_id": "mckinsey-consulting-report",
                    "style_source": "built-in-style-library",
                    "visual_signature": "crisp consulting system diagram",
                    "layout_archetype": "single system diagram",
                    "evidence_presentation": "one proof object with supporting label",
                    "composition_grammar": "center-left diagram with sparse annotations",
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
                    "raw_comp_path": "slides/raw/slide-001-raw.png",
                    "upscale_manifest_path": upscale_manifest,
                    "image_source_type": "imagegen",
                    "visual_archetype": "diagram",
                    "clarity_review": {
                        "status": "approved",
                        "blocking_blur": False,
                        "image_dimensions_px": {"width": 3840, "height": 2160},
                        "image_file_size_bytes": slide_path.stat().st_size,
                        "upscale_manifest_path": upscale_manifest,
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
            "raw_source_image_path": "slides/raw/slide-001-raw.png",
            "upscale_manifest_path": upscale_manifest,
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
            self.assertTrue((workspace / "scripts" / "realesrgan_upscale.py").exists())
            self.assertTrue((workspace / "conversion_manifest.json").exists())
            self.assertFalse((workspace / "reconstruction_manifest.json").exists())
            manifest = json.loads((workspace / "conversion_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["conversion_method"], "strict_slide_image_to_editable_pptx")
            self.assertTrue(manifest["global_rules"]["icon_hd_enhancement_required"])
            self.assertTrue(manifest["global_rules"]["source_comp_realesrgan_4k_required"])
            self.assertTrue(manifest["global_rules"]["icon_realesrgan_upscale_required"])
            self.assertTrue(manifest["tool_files"]["copied_to_workspace"]["scripts/realesrgan_upscale.py"])
            icon_jobs = json.loads((workspace / "icons" / "icon_jobs.json").read_text(encoding="utf-8"))
            self.assertEqual(icon_jobs["minimum_output_icon_min_dim_px"], 256)
            self.assertEqual(icon_jobs["icon_hd_target_min_px"], 256)
            self.assertTrue(icon_jobs["realesrgan_upscale_required"])
            self.assertEqual(icon_jobs["icon_upscale_method"], "python-realesrganer")
            self.assertEqual(icon_jobs["realesrgan_device"], "cpu")
            self.assertEqual(icon_jobs["realesrgan_tile"], 400)

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

    def test_before_pptx_gate_rejects_missing_realesrgan_comp_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = init_workspace(Path(tmp))
            lock_direct_conversion_workspace(workspace)
            manifest_path = workspace / "conversion_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            missing = workspace / manifest["slides"][0]["upscale_manifest_path"]
            missing.unlink()
            payload = run_json(
                [sys.executable, str(GATE_SCRIPT), "--workspace", str(workspace), "--stage", "before-pptx"],
                check=False,
            )
            self.assertEqual(payload["status"], "FAIL")
            self.assertTrue(any("Real-ESRGAN manifest" in item for item in payload["failures"]))

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

    def test_style_gate_rejects_near_identical_layout_archetypes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = init_workspace(Path(tmp), mode="create")
            lock_generated_comp_workspace(workspace)
            duplicate_sheet = workspace / "styles" / "lane-b-contact-sheet.png"
            write_noise_png(duplicate_sheet, width=2400, height=1350)

            style_path = workspace / "style_brief.json"
            style = json.loads(style_path.read_text(encoding="utf-8"))
            base = style["candidate_directions"][0]
            style.update({"direction_count": 2, "selected_options": ["option-a", "option-b"]})
            style["candidate_directions"] = [
                base,
                {
                    **base,
                    "option_id": "option-b",
                    "style_lane_id": "lane-b",
                    "style_id": "thesis-defense-clean",
                    "aesthetic_family": "academic",
                    "visual_signature": "calm defense deck using the same center-loop skeleton",
                    "task_fit": {
                        "profile_match": True,
                        "fit_reason": "Still presented as a task-fit option for the smoke failure case.",
                        "profile_signals_used": ["internal-review", "proof object: diagram"],
                    },
                    "layout_archetype": base["layout_archetype"],
                    "evidence_presentation": base["evidence_presentation"],
                    "composition_grammar": base["composition_grammar"],
                },
            ]
            style["style_contact_sheets"].append(
                {
                    "path": "styles/lane-b-contact-sheet.png",
                    "generator": "imagegen",
                    "style_id": "thesis-defense-clean",
                    "style_source": "built-in-style-library",
                    "visual_signature": "calm defense deck using the same center-loop skeleton",
                    "layout_archetype": base["layout_archetype"],
                    "evidence_presentation": base["evidence_presentation"],
                    "composition_grammar": base["composition_grammar"],
                }
            )
            style_path.write_text(json.dumps(style, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            payload = run_json(
                [sys.executable, str(GATE_SCRIPT), "--workspace", str(workspace), "--stage", "style-selection"],
                check=False,
            )
            self.assertEqual(payload["status"], "FAIL")
            self.assertTrue(any("layout_archetype" in item for item in payload["failures"]))
            self.assertTrue(any("evidence_presentation" in item for item in payload["failures"]))

    def test_style_gate_accepts_company_profile_route_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = init_workspace(Path(tmp), mode="create")
            lock_generated_comp_workspace(workspace)
            style_path = workspace / "style_brief.json"
            style = json.loads(style_path.read_text(encoding="utf-8"))
            style.update(
                {
                    "deck_profile": "company-profile",
                    "deck_profile_evidence": {
                        "primary_profile": "company-profile",
                        "secondary_profiles": [],
                        "audience": "enterprise customers",
                        "occasion": "company introduction deck",
                        "source_signals": ["企业介绍", "company capabilities", "brand trust proof"],
                        "excluded_style_families": ["personal-brand", "academic"],
                        "notes": "Company profile should use company/corporate route styles.",
                    },
                }
            )
            candidate = style["candidate_directions"][0]
            candidate.update(
                {
                    "style_id": "corporate-profile-architectural",
                    "aesthetic_family": "company-profile",
                    "visual_signature": "architectural company profile with capability proof",
                    "task_fit": {
                        "profile_match": True,
                        "fit_reason": "Enterprise company introduction needs corporate capability, trust, and scale signals.",
                        "profile_signals_used": ["company-profile", "企业介绍", "enterprise customers"],
                    },
                    "layout_archetype": "company capability map",
                    "evidence_presentation": "capability proof modules with trust metrics",
                    "composition_grammar": "corporate hero plus structured proof grid",
                    "density_and_pacing": "moderate enterprise introduction density",
                    "thumbnail_differentiators": ["corporate hero", "capability proof map"],
                    "must_not_reuse": "Do not reuse personal promotion or academic defense skeletons.",
                }
            )
            style["style_contact_sheets"][0].update(
                {
                    "style_id": "corporate-profile-architectural",
                    "aesthetic_family": "company-profile",
                    "visual_signature": "architectural company profile with capability proof",
                    "layout_archetype": "company capability map",
                    "evidence_presentation": "capability proof modules with trust metrics",
                    "composition_grammar": "corporate hero plus structured proof grid",
                }
            )
            style_path.write_text(json.dumps(style, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            payload = run_json([sys.executable, str(GATE_SCRIPT), "--workspace", str(workspace), "--stage", "style-selection"])
            self.assertEqual(payload["status"], "PASS", payload["failures"])

    def test_style_gate_rejects_unrequested_personal_style_for_company_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = init_workspace(Path(tmp), mode="create")
            lock_generated_comp_workspace(workspace)
            style_path = workspace / "style_brief.json"
            style = json.loads(style_path.read_text(encoding="utf-8"))
            style.update(
                {
                    "deck_profile": "company-profile",
                    "deck_profile_evidence": {
                        "primary_profile": "company-profile",
                        "secondary_profiles": [],
                        "audience": "enterprise customers",
                        "occasion": "company introduction deck",
                        "source_signals": ["企业介绍", "company capabilities", "brand trust proof"],
                        "excluded_style_families": ["personal-brand", "academic"],
                        "notes": "This fixture intentionally uses an off-profile personal style.",
                    },
                }
            )
            candidate = style["candidate_directions"][0]
            candidate.update(
                {
                    "style_id": "promotion-defense-evidence",
                    "aesthetic_family": "personal-brand",
                    "visual_signature": "personal promotion proof spine misapplied to company intro",
                    "task_fit": {
                        "profile_match": True,
                        "fit_reason": "Intentionally wrong for the smoke failure case.",
                        "profile_signals_used": ["company-profile", "企业介绍"],
                    },
                    "layout_archetype": "personal achievement proof spine",
                    "evidence_presentation": "individual achievement milestones",
                    "composition_grammar": "promotion defense ladder",
                    "density_and_pacing": "personal review cadence",
                    "thumbnail_differentiators": ["personal proof spine", "promotion ladder"],
                    "must_not_reuse": "Do not use for company intro.",
                }
            )
            style["style_contact_sheets"][0].update(
                {
                    "style_id": "promotion-defense-evidence",
                    "aesthetic_family": "personal-brand",
                    "visual_signature": "personal promotion proof spine misapplied to company intro",
                    "layout_archetype": "personal achievement proof spine",
                    "evidence_presentation": "individual achievement milestones",
                    "composition_grammar": "promotion defense ladder",
                }
            )
            style_path.write_text(json.dumps(style, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            payload = run_json(
                [sys.executable, str(GATE_SCRIPT), "--workspace", str(workspace), "--stage", "style-selection"],
                check=False,
            )
            self.assertEqual(payload["status"], "FAIL")
            self.assertTrue(any("off-profile for company-profile" in item for item in payload["failures"]))

    def test_style_gate_accepts_user_requested_off_profile_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = init_workspace(Path(tmp), mode="create")
            lock_generated_comp_workspace(workspace)
            style_path = workspace / "style_brief.json"
            style = json.loads(style_path.read_text(encoding="utf-8"))
            style.update(
                {
                    "deck_profile": "company-profile",
                    "deck_profile_evidence": {
                        "primary_profile": "company-profile",
                        "secondary_profiles": [],
                        "audience": "enterprise customers",
                        "occasion": "company introduction deck",
                        "source_signals": ["企业介绍", "company capabilities", "brand trust proof"],
                        "excluded_style_families": [],
                        "notes": "User explicitly requested promotion-defense style despite company-profile task.",
                    },
                    "user_style_preferences": {
                        "requested_aesthetic_families": [],
                        "requested_style_ids": ["promotion-defense-evidence"],
                        "forbidden_aesthetic_families": [],
                        "forbidden_style_ids": [],
                        "notes": "User explicitly requested this off-profile style.",
                    },
                }
            )
            candidate = style["candidate_directions"][0]
            candidate.update(
                {
                    "style_id": "promotion-defense-evidence",
                    "aesthetic_family": "personal-brand",
                    "visual_signature": "promotion proof spine adapted to company introduction content",
                    "task_fit": {
                        "profile_match": False,
                        "user_requested_off_profile": True,
                        "fit_reason": "Off-profile by route, but the user explicitly requested promotion-defense style.",
                        "profile_signals_used": ["company-profile", "user requested promotion-defense-evidence"],
                    },
                    "layout_archetype": "achievement proof spine",
                    "evidence_presentation": "milestone impact evidence",
                    "composition_grammar": "promotion defense ladder adapted to company proof",
                    "density_and_pacing": "moderate proof-led cadence",
                    "thumbnail_differentiators": ["proof spine", "promotion-style ladder"],
                    "must_not_reuse": "Honor requested style without changing company intro claims.",
                }
            )
            style["style_contact_sheets"][0].update(
                {
                    "style_id": "promotion-defense-evidence",
                    "aesthetic_family": "personal-brand",
                    "visual_signature": "promotion proof spine adapted to company introduction content",
                    "layout_archetype": "achievement proof spine",
                    "evidence_presentation": "milestone impact evidence",
                    "composition_grammar": "promotion defense ladder adapted to company proof",
                }
            )
            style_path.write_text(json.dumps(style, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            payload = run_json([sys.executable, str(GATE_SCRIPT), "--workspace", str(workspace), "--stage", "style-selection"])
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
