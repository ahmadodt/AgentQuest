# AgentQuest Case Study

## Project Framing

AgentQuest is a deterministic evaluation environment for small, quantized local language models. The project uses a fantasy RPG wrapper, but the actual engineering goal is more specific: measure whether a model can choose valid structured tool calls, reason over partial information, and recover after failure.

The key constraint is deliberate. Runs are designed around local `.gguf` models instead of hosted frontier APIs so the benchmark reflects low-cost, inspectable, reproducible inference.

## Main Question

How much structured reasoning survives when smaller quantized models must:

- choose from only the tools visible in the scene
- return strict JSON instead of prose
- act under different prompt visibility presets
- recover from failure by writing notes and retrying

## Why The Presets Matter

The prompt presets are the main experimental lever. They let you test whether a small model performs better when it sees less information, the right amount of information, or nearly everything.

The portfolio story should focus on these comparisons:

- `BLIND_ADVENTURER`: minimal information, stronger pressure on inference
- `BATTLE_PLAN`: balanced information for benchmark-style comparison
- `FULL_INFO`: maximal debug-style visibility to test overload vs. helpful context

This is the most direct way to show whether the model is reasoning from the right information or simply collapsing when the prompt gets denser.

## Benchmark Recipe

Use one fixed slice for the flagship LinkedIn post:

- Campaign: `campaign.goblin_den_v1`
- Character: `knight.bram`
- Prompt format: `json_only`
- Presets: `BLIND_ADVENTURER`, `BATTLE_PLAN`, `FULL_INFO`
- Models: at least 3 quantized local models

Recommended workflow:

```bash
python scripts/run_benchmark.py --campaign-id campaign.goblin_den_v1 --character-id knight.bram --preset BLIND_ADVENTURER --preset BATTLE_PLAN --preset FULL_INFO --prompt-format json_only --model qwen3_4b_q4_k_m --output-dir results\\benchmarks\\portfolio\\qwen3_4b
python scripts/run_benchmark.py --campaign-id campaign.goblin_den_v1 --character-id knight.bram --preset BLIND_ADVENTURER --preset BATTLE_PLAN --preset FULL_INFO --prompt-format json_only --model qwen2_5_3b_instruct_q5_k_m --output-dir results\\benchmarks\\portfolio\\qwen2_5_3b
python scripts/run_benchmark.py --campaign-id campaign.goblin_den_v1 --character-id knight.bram --preset BLIND_ADVENTURER --preset BATTLE_PLAN --preset FULL_INFO --prompt-format json_only --model llama_3_2_3b_instruct_q4_k_m --output-dir results\\benchmarks\\portfolio\\llama_3_2_3b
python scripts/render_benchmark_report.py --benchmark-dir results\\benchmarks\\portfolio\\qwen3_4b --label "Qwen3 4B" --benchmark-dir results\\benchmarks\\portfolio\\qwen2_5_3b --label "Qwen2.5 3B" --benchmark-dir results\\benchmarks\\portfolio\\llama_3_2_3b --label "Llama 3.2 3B" --output docs\\portfolio_assets\\benchmark_report.md --summary-json docs\\portfolio_assets\\benchmark_report.json
```

## What To Report

The first post should answer:

- Which model had the highest success rate?
- Which preset helped the smaller models most?
- Did extra context improve legal tool choice, scene reasoning, or both?
- Were failures mostly parse failures, illegal actions, or poor tactical choices?

Keep the main post focused on a few hard numbers:

- success rate
- parse failure count
- dominant failure codes
- one representative success and one representative failure

## Self-Learning Follow-Up

Treat self-learning as the second story, not the first. The question here is not "does retry exist?" but "are the notes specific enough to change later behavior?"

Suggested comparison:

```bash
python -m src.runner.run_campaign --campaign-id campaign.goblin_den_v1 --character-id knight.bram --preset BATTLE_PLAN --prompt-format json_only --save-run runs\\portfolio\\baseline_campaign.json
python -m src.runner.run_campaign --campaign-id campaign.goblin_den_v1 --character-id knight.bram --preset BATTLE_PLAN --prompt-format json_only --self-learning --per-scene-retry-limit 3 --total-retry-limit 20 --save-run runs\\portfolio\\self_learning_campaign.json
```

Evaluate the notes on these criteria:

- Do they name the actual cause of failure?
- Do they avoid generic filler?
- Does the later tool choice change?
- Does the final success rate improve?

## Tool-Calling Walkthrough

Use one screenshot or short walkthrough to show:

1. the scene and visible tools
2. the model's raw JSON output
3. the parsed tool call
4. the validator verdict and reason

This is the easiest way to make the project legible to non-specialists without flattening the engineering detail.

## Portfolio Assets Checklist

Before posting, prepare:

- one architecture diagram
- one Streamlit screenshot showing the validator path
- one generated benchmark report covering 3 models
- one table or chart for preset comparison
- one saved self-learning example with note quality commentary

## Positioning Notes

Lead with this idea:

"I built a deterministic tool-use evaluator to test how small quantized local models reason under different information constraints."

Do not lead with:

- "I made a game with AI"
- "I built a Streamlit app"
- "I ran a local model"

Those are true, but they undersell the actual systems and evaluation work.
