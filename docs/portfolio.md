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
