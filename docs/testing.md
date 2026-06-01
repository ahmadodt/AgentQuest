# Testing

Run the full test suite:

```bash
pytest
```

Run focused test files:

```bash
python -m pytest tests/test_streamlit_utils.py
python -m pytest tests/test_model_registry.py
python -m pytest tests/test_ast_validator.py
```

## What Tests Cover

Current tests cover:

- loader merge behavior
- AST, hard, soft, and pipeline validation
- campaign runner behavior
- model registry and catalog behavior
- Streamlit utility helpers
- benchmark utility helpers
- Open5e conversion

## Deterministic Validation Report

Use the deterministic validation report to check whether each scene/character pair has at least one valid tool:

```bash
python scripts/generate_validation_report.py
```

Optional data-dir override:

```bash
python scripts/generate_validation_report.py --data-dir data
```

The report prints valid and invalid tool counts per scene/character pair and exits non-zero if any pair is unsolved.

## Prompt Inspection

Use prompt preview before debugging model behavior:

```bash
python -m src.runner.preview_prompt --preset BATTLE_PLAN
```

`preview_prompt` does not call the model. It is the safest way to confirm the prompt contains the expected scene, monster, character, and tool visibility.
