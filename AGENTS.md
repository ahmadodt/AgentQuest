# AgentQuest Codex Instructions

## Project focus

AgentQuest is a playable AI-agent RPG where an LLM chooses structured tool calls and the engine validates the result.

The project should stay runner-first and evaluation-friendly. The UI should remain a thin layer over the existing engine, loader, prompt builder, model backend, validator, and runner/service code.

## Important directories

Prefer inspecting these directories first when working on normal development tasks:

- `src/prompts/`: prompt construction and rendering
- `src/engine/`: loader and validation pipeline
- `src/models/`: model backend interfaces and adapters
- `src/runner/`: scripts/services for previewing prompts, running one scene, and running campaigns
- `src/app/`: Streamlit UI and app entrypoints
- `configs/`: runtime configuration
- `data/custom/agentquest/`: hand-authored game data
- `tests/`: unit tests
- `README.md`
- `pyproject.toml`

## Context limits

Before editing, inspect only the smallest set of files needed for the task.

Avoid broad repository scans. Do not recursively inspect large data folders, generated files, run logs, virtual environments, caches, or local model directories unless the user explicitly asks.

## Do not read or modify

Do not read, summarize, edit, or inspect local model weight files.

Ignored model locations and file types:

- `local_models/`
- `models/`
- `*.gguf`
- `*.safetensors`
- `*.bin`

Do not include model files in commits.

## Data folders

Do not read, summarize, edit, or inspect these folders unless the task is specifically about data conversion, Open5e ingestion, generated data debugging, or dataset cleanup:

- `data/raw/`
- `data/generated/`
- `data/curated/`

Especially avoid opening large Open5e JSON files such as:

- `data/raw/open5e/*.json`
- `data/generated/open5e/*.json`
- `data/curated/open5e/*.json`

For normal development, prefer small custom examples under:

- `data/custom/agentquest/`

## Generated and debug files

Treat these as generated/debug outputs unless explicitly requested:

- `runs/*.json`
- `runs/*.jsonl`
- `.pytest_cache/`
- `__pycache__/`
- `*.pyc`

Do not inspect old run logs unless the user specifically asks to debug a previous run.

## Virtual environments and caches

Do not read or inspect:

- `.venv/`
- `venv/`
- `myenv/`
- `.mypy_cache/`
- `.ruff_cache/`
- `.streamlit/secrets.toml`

## Development rules

Do not change validator semantics unless the user explicitly asks.

Do not change Open5e conversion logic unless the task is specifically about the Open5e pipeline.

Do not move or rename major data fields unless necessary.

Prefer small, reviewable changes.

Prefer simple Python over clever abstractions.

Do not add new dependencies unless the task clearly requires them.

Use `os.path` for path handling when editing this project.

## Runner and UI rules

Keep CLI runners working.

If Streamlit needs runner behavior, prefer using shared service functions instead of duplicating runner logic inside the UI.

The Streamlit UI should display engine outputs clearly, but should not become the source of truth for validation or campaign rules.

## Commit message format

Use the existing conventional commit style.

Allowed prefixes include:

- `feat:`
- `fix:`
- `refactor:`
- `docs:`
- `test:`
- `chore:`

Examples:

- `feat: add continue-on-failure campaign mode`
- `fix: resolve streamlit import path issue`
- `refactor: extract shared campaign run service`
- `docs: update streamlit run instructions`



Documentation rules

The top-level README.md is only for:

Project overview
Quick start
Basic installation
Common commands
Links to deeper documentation

Detailed documentation must go into docs/.

Use this structure:

docs/architecture.md for architecture and component relationships
docs/development.md for local development workflow
docs/testing.md for testing strategy and commands
docs/docker.md for Docker setup and container behavior
docs/decisions/ for architectural decision records
Module-level README.md files only when a directory needs local explanation

Do not write all documentation into one file.

When adding documentation:

Put it in the most specific existing document.
Create a new document only if the topic does not fit anywhere.
Link new documents from the relevant index or README.
Keep documentation close to the code it explains when possible.

Planning rule

For multi-file changes, first produce a short plan with:

Files likely to change
Why each file needs to change
Tests or validation to run

Mistakes to avoid
Do not dump all new documentation into README.md.
Do not create a new top-level markdown file for every small topic.
Do not create duplicate utilities when a shared helper already exists.
Do not silently change APIs, CLI commands, config names, or output formats.
Do not remove comments or documentation unless they are wrong or obsolete.
Do not replace working code with a larger rewrite just to make it look cleaner.
Do not invent commands; inspect project files first.
Response format after completing work

When finished, report:

What changed
Files modified
Tests or checks run
Any remaining risks or follow-up tasks