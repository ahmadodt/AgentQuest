# AgentQuest Codex Instructions

## Project focus

AgentQuest is a playable AI-agent RPG where an LLM chooses structured tool calls and the engine validates the result.

## Important directories

- `src/prompts/`: prompt construction and rendering
- `src/engine/`: loader and validation pipeline
- `src/models/`: model backend interfaces and adapters
- `src/runner/`: scripts for previewing prompts and running one scene
- `tests/`: unit tests

## Do not read or modify

Do not read, summarize, edit, or inspect local model weight files.

Ignored model locations and file types:

- `local_models/`
- `*.gguf`
- `*.safetensors`
- `*.bin`
- `data\raw\open5e\*.json`
Do not include model files in commits.

## Generated files

Treat these as generated/debug outputs unless explicitly requested:

- `runs/*.json`
- `runs/*.jsonl`
- `.pytest_cache/`
- `__pycache__/`


for git commits ues the already exisitng format for commmits: fix: or refactor: or feat: or docs:....