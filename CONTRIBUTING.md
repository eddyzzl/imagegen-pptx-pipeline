# Contributing

Contributions should keep the installable skill concise and the open-source repository easy to validate.

## Principles

- Keep runtime instructions inside `imagegen-pptx-pipeline/SKILL.md` and `references/`.
- Keep repository docs at the repository root, not inside the installable skill directory.
- Add deterministic checks to `scripts/` when a rule is important enough to block output.
- Prefer schemas and gate checks over prose-only requirements.
- Do not add private templates, user data, company materials, generated customer decks, or personal paths.

## Adding A Deck Profile

1. Add the profile to `SKILL.md`.
2. Add schema expectations to `references/schemas.md` if needed.
3. Add profile-specific visual guidance to `references/taste-system.md`.
4. Add prompt wording to `references/prompt-templates.md`.
5. Add or update smoke tests when the gate behavior changes.

## Adding A Reviewer Role

1. Add the role to `references/subagent-rubrics.md`.
2. Add it to the stage matrix only where it is required.
3. Define P0/P1 blockers clearly.
4. Keep output in the shared Feedback JSON format.

## Validation Before PR

```bash
python -m py_compile imagegen-pptx-pipeline/scripts/*.py
python -m unittest discover -s tests
```

Also run a privacy scan:

```bash
rg -n "/Users/|\\\\Users\\\\|secret|token|api[_-]?key|password|PRIVATE|CONFIDENTIAL" .
```

Review any matches before publishing.

