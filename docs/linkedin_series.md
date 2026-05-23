# LinkedIn Series Plan

## Post 1: Main Portfolio Post

Headline:

"How well can small quantized LLMs reason when they must choose valid tool calls instead of generating free-form text?"

Include:

- one-sentence project framing
- one architecture diagram
- one benchmark result table across 3 models
- one short point on prompt presets
- one screenshot of the validator/tool-call flow

Primary message:

AgentQuest is an evaluation environment for structured reasoning, not just a game wrapper.

## Post 2: Self-Learning Notes

Headline:

"Can a small local model write useful notes after failure and actually improve on retry?"

Include:

- baseline vs self-learning success rate
- one strong note example
- one weak note example
- whether behavior changed on retry

Primary message:

Retry loops are only interesting if the model's notes are specific enough to improve the next decision.

## Post 3: Preset Tradeoffs

Headline:

"More context is not always better: prompt visibility presets changed how the same model behaved."

Include:

- preset comparison table
- one example where extra info helped
- one example where extra info overloaded the model

Primary message:

Prompt design for small models is not just about adding more information.

## Post 4: Tool Calling Walkthrough

Headline:

"What 'structured tool calling' actually looks like in a local RPG-style evaluator."

Include:

- scene input
- visible tools
- raw JSON output
- hard/soft validation outcome

Primary message:

Structured outputs become much easier to debug when the action space and failure reasons are explicit.
