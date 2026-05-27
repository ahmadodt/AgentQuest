import json
import os
from dataclasses import dataclass


DEFAULT_MODEL_CATALOG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "configs", "model_catalog.json")
)


@dataclass(frozen=True)
class ModelCatalogEntry:
    name: str
    display_name: str
    backend: str
    repo_id: str
    filename: str
    description: str = ""


def load_model_catalog(
    catalog_path: str = DEFAULT_MODEL_CATALOG_PATH,
) -> dict[str, ModelCatalogEntry]:
    resolved_catalog_path = os.path.abspath(catalog_path)
    with open(resolved_catalog_path, "r", encoding="utf-8") as file_obj:
        raw = json.load(file_obj)

    models = raw.get("models")
    if not isinstance(models, list):
        raise ValueError("model_catalog.json must contain a top-level 'models' list.")

    catalog: dict[str, ModelCatalogEntry] = {}
    for index, item in enumerate(models):
        if not isinstance(item, dict):
            raise ValueError(f"Catalog entry {index} must be an object.")

        name = str(item.get("name") or "").strip()
        display_name = str(item.get("display_name") or "").strip()
        backend = str(item.get("backend") or "").strip()
        repo_id = str(item.get("repo_id") or "").strip()
        filename = str(item.get("filename") or "").strip()
        description = str(item.get("description") or "").strip()

        if not name or not display_name or not backend or not repo_id or not filename:
            raise ValueError(
                "Each model catalog entry must define non-empty 'name', "
                "'display_name', 'backend', 'repo_id', and 'filename' fields."
            )
        if name in catalog:
            raise ValueError(f"Duplicate model catalog entry name: {name}")

        catalog[name] = ModelCatalogEntry(
            name=name,
            display_name=display_name,
            backend=backend,
            repo_id=repo_id,
            filename=filename,
            description=description,
        )

    return catalog


def resolve_model_catalog_entry(
    model_name: str,
    *,
    catalog_path: str = DEFAULT_MODEL_CATALOG_PATH,
) -> ModelCatalogEntry:
    normalized_model_name = (model_name or "").strip()
    if not normalized_model_name:
        raise ValueError("Model name must be a non-empty string.")

    catalog = load_model_catalog(catalog_path)
    try:
        return catalog[normalized_model_name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown model '{normalized_model_name}'. Add it to {os.path.abspath(catalog_path)}."
        ) from exc
