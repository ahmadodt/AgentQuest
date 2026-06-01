# Docker

The Docker flow is for local/demo use of the Streamlit app.

## Build

Create a local environment file:

```bash
copy .env.example .env
```

Build the image:

```bash
docker compose build
```

## Run

Start the app:

```bash
docker compose up
```

Then open `http://localhost:8501`.

## Runtime Settings

The compose setup passes the same runtime settings used by local execution:

- `AGENTQUEST_DATA_DIR=/app/data`
- `AGENTQUEST_MODEL=qwen3_4b_q4_k_m`
- `AGENTQUEST_MODELS_DIR=/app/local_models`
- `AGENTQUEST_RUNS_DIR=/app/runs`
- Streamlit host, port, and headless settings

Model aliases resolve through `configs/model_catalog.json`. Model files are downloaded or loaded by the llama.cpp backend according to the catalog entry.

## Mounted Volumes

The compose file mounts:

- `./data` to `/app/data`
- `./local_models` to `/app/local_models` as read-only
- `./runs` to `/app/runs`

This keeps runtime data editable, keeps large model files out of the image, and preserves run logs between container restarts.

## Files

- `Dockerfile`: installs the package, Streamlit dependencies, and `llama-cpp-python`.
- `docker-compose.yml`: defines environment variables, port mapping, and mounted volumes.
- `.env.example`: documents compose-time environment values.
- `.dockerignore`: keeps local models, data, runs, caches, and virtualenvs out of the build context.
