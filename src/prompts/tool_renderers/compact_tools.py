import json
from typing import Any, Dict, List

from src.prompts.prompt_config import PromptConfig


def _fmt_rule(k: str, schema: Dict[str, Any]) -> str:
    """
    Render a single argument rule in a JSON-clean way.
    Example:
      - target: string
      - direction: string, enum=["front","left"]
      - power: integer, min=1, max=5
    """
    t = schema.get("type", "any")
    bits = [t]

    if "enum" in schema:
        bits.append(f"enum={json.dumps(schema['enum'])}")

    if t in ("integer", "number"):
        if "minimum" in schema:
            bits.append(f"min={schema['minimum']}")
        if "maximum" in schema:
            bits.append(f"max={schema['maximum']}")

    return f"{k}: " + ", ".join(bits)


def render_tools_compact(tools: List[Dict[str, Any]], cfg: PromptConfig) -> str:
    lines: List[str] = []

    for tool in tools:
        tool_id = tool.get("tool_id", "")
        desc = tool.get("description", "")

        header = f"- tool_id: {tool_id}"

        if cfg.tools_include_label_emoji:
            label = tool.get("label", "") or ""
            emoji = ""
            ui = tool.get("ui") or {}
            if isinstance(ui, dict):
                emoji = ui.get("emoji", "") or ""
            if label or emoji:
                pretty = f"{emoji} {label}".strip()
                header += f" ({pretty})"

        lines.append(header)

        # Always include description
        if desc:
            lines.append(f"  desc: {desc}")

        # Always include args schema
        args = tool.get("args", {}) or {}
        props = args.get("properties") or {}
        required = args.get("required") or []

        if props:
            lines.append(f"  args_required: {json.dumps(required)}")
            lines.append("  args_schema:")
            for k, schema in props.items():
                lines.append(f"    - {_fmt_rule(k, schema)}")
        else:
            lines.append("  args_required: []")
            lines.append("  args_schema: (none)")

        # Optional: constraints (JSON-clean)
        if cfg.tools_include_constraints:
            constraints = tool.get("constraints") or {}
            if isinstance(constraints, dict) and constraints:
                lines.append(f"  constraints: {json.dumps(constraints)}")

        # Optional: effects (JSON-clean)
        if cfg.tools_include_effects:
            effects = tool.get("effects") or {}
            if isinstance(effects, dict) and effects:
                lines.append(f"  effects: {json.dumps(effects)}")

        lines.append("")

    return "\n".join(lines).strip()