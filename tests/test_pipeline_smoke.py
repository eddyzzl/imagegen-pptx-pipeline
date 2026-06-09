from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "imagegen-pptx-pipeline"
INIT_SCRIPT = SKILL_DIR / "scripts" / "init_pipeline_workspace.py"
GATE_SCRIPT = SKILL_DIR / "scripts" / "check_pipeline_gates.py"


def load_gate_module():
    spec = importlib.util.spec_from_file_location("check_pipeline_gates", GATE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def run_json(args: list[str], *, check: bool = True) -> dict:
    completed = subprocess.run(args, check=check, text=True, capture_output=True)
    return json.loads(completed.stdout)


class PipelineSmokeTests(unittest.TestCase):
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

    def test_visual_contract_requires_pixel_locked_hybrid_plan(self) -> None:
        gate_module = load_gate_module()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "slides").mkdir()
            (workspace / "styles").mkdir()
            comp = workspace / "slides" / "slide-001-comp.png"
            comp.write_bytes(b"fake image bytes")
            contact = workspace / "styles" / "option-a-contact-sheet.png"
            contact.write_bytes(b"fake image bytes")
            deck_spec = {
                "deck": {"slide_count": 1},
                "slides": [{"slide_id": "slide-001"}],
            }
            visual_contract = {
                "selected_style": "Option A",
                "contact_sheet": "styles/option-a-contact-sheet.png",
                "per_slide_comps_complete": True,
                "default_reconstruction_mode": "pixel_locked_hybrid",
                "pixel_locked_hybrid_required": True,
                "slides": [
                    {
                        "slide_id": "slide-001",
                        "comp_path": "slides/slide-001-comp.png",
                        "visual_archetype": "system map",
                        "reconstruction_mode": "pixel_locked_hybrid",
                    }
                ],
            }
            failures: list[str] = []
            gate_module.check_visual_contract(workspace, deck_spec, visual_contract, failures)
            self.assertTrue(any("comp_backplate.strategy" in item for item in failures))
            self.assertTrue(any("text_mask_plan" in item for item in failures))
            self.assertTrue(any("editable_overlay_plan" in item for item in failures))

            visual_contract["slides"][0].update(
                {
                    "comp_backplate": {
                        "strategy": "full_slide",
                        "path": "slides/slide-001-comp.png",
                        "insert_first": True,
                        "covers_full_slide": True,
                    },
                    "text_mask_plan": [
                        {"region": "title", "method": "shape mask", "reason": "editable title overlay"}
                    ],
                    "editable_overlay_plan": ["editable title", "editable key number"],
                }
            )
            failures = []
            gate_module.check_visual_contract(workspace, deck_spec, visual_contract, failures)
            self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
