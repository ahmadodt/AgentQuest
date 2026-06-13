# Portfolio Materials

AgentQuest includes portfolio notes and publishable drafts, but they are separate from the main developer documentation.

Start here:

- Case study: `docs/case_study.md`
- LinkedIn flagship post draft: `docs/linkedin_flagship_post.md`
- LinkedIn follow-up series: `docs/linkedin_series.md`
- Portfolio assets: `docs/portfolio_assets/README.md`

## Recommended Story

Lead with AgentQuest as a deterministic tool-use evaluator for small quantized local models.

The strongest current benchmark story compares:

- 3 local GGUF-backed model aliases from `configs/model_catalog.json`
- `BLIND_ADVENTURER`, `BATTLE_PLAN`, and `FULL_INFO`
- strict `json_only` responses
- parse failures, hard-validation failures, and soft reasoning failures

The RPG wrapper should support the story, not replace it. The key point is inspectable structured reasoning under constrained tool use.

## Results Showcase

The Streamlit `Results Showcase` page works without model weights. It combines stable committed bundles from `showcase/benchmarks/` with local history from `results/benchmarks/` when that directory exists.

Each benchmark manifest records a SHA-256 fingerprint and per-file data versions. An exact match means the benchmark used the current custom dataset byte-for-byte. Mismatched historical runs remain useful as snapshots, but the UI labels them and does not present them as equivalent current-data evidence.
