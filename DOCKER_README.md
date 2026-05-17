# Docker Notes

This file explains the Docker-related setup currently in the repository and what each piece is doing.

## Files Added Or Updated For Docker

- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `.dockerignore`

## What The Docker Setup Does

The Docker flow is designed for local/demo use of the Streamlit app.

The container:

- starts from `python:3.11-slim`
- installs system build tools needed for Python packages like `llama-cpp-python`
- copies the repository into `/app`
- installs the project package with `pip install .`
- installs `llama-cpp-python`
- runs `streamlit run streamlit_app.py`

The exposed app port is `8501` by default.

## Why `docker-compose.yml` Exists

`docker-compose.yml` provides a simple way to run the app with the expected environment variables and mounted folders.

It sets:

- `AGENTQUEST_DATA_DIR=/app/data`
- `AGENTQUEST_MODEL_PATH=/app/local_models/...gguf`
- `AGENTQUEST_MODELS_DIR=/app/local_models`
- `AGENTQUEST_RUNS_DIR=/app/runs`
- Streamlit host/port/headless settings

It also maps the Streamlit port from the container to the host.

## Why These Volumes Are Mounted

The compose file mounts three local folders:

- `./data -> /app/data`
- `./local_models -> /app/local_models` as read-only
- `./runs -> /app/runs`

This keeps important runtime files outside the image:

- game/runtime data stays editable on the host
- GGUF model files are not baked into the image
- run logs persist between container restarts

The `local_models` mount is read-only because the container only needs to load models, not modify them.

## Why `.dockerignore` Excludes Data And Models

`.dockerignore` excludes:

- `local_models`
- `data`
- `runs`
- git metadata, caches, and virtualenv folders

This keeps the build context smaller and avoids copying large local assets into the image.

In particular:

- model files are not sent to Docker during build
- runtime data is expected to come from the mounted host folder
- run outputs are written to the mounted host folder instead of becoming image content

## Why `.env.example` Exists

`.env.example` documents the environment variables expected by the compose setup.

You can copy it to `.env` and adjust values if needed, especially:

- the selected GGUF model path
- the Streamlit port

## Practical Result

After building and starting the container with `docker compose up`, the repo runs as a containerized Streamlit app that:

- reads game data from the host `data/` folder
- reads GGUF models from the host `local_models/` folder
- writes run logs to the host `runs/` folder

That keeps the image generic and keeps large or changing local assets outside the image.
