from typing import Any, Dict, List


def _fmt_rule(k: str, schema: Dict[str, Any]) -> str:
    t = schema.get("type", "any")
    bits = [t]

    if "enum" in schema:
        bits.append(f"enum={schema['enum']}")

    if t in ("integer", "number"):
        if "minimum" in schema:
            bits.append(f"min={schema['minimum']}")
        if "maximum" in schema:
            bits.append(f"max={schema['maximum']}")

    return f"{k}: " + ", ".join(bits)


def render_tools_compact(tools: List[Dict[str, Any]]) -> str:
    lines: List[str] = []

    for tool in tools:
        tool_id = tool.get("tool_id", "")
        desc = tool.get("description", "")

        label = tool.get("label", "") or ""
        emoji = ""
        ui = tool.get("ui") or {}
        if isinstance(ui, dict):
            emoji = ui.get("emoji", "") or ""

        header = f"- tool_id: {tool_id}"
        if label or emoji:
            # e.g. "- tool_id: wizard.cast_fireball (🔥 Cast Fireball)"
            pretty = f"{emoji} {label}".strip()
            header += f" ({pretty})"
        lines.append(header)

        if desc:
            lines.append(f"  desc: {desc}")

        args = tool.get("args", {}) or {}
        props = (args.get("properties") or {})
        required = args.get("required") or []

        if props:
            lines.append(f"  args_required: {required}")
            lines.append("  args_schema:")
            for k, schema in props.items():
                lines.append(f"    - {_fmt_rule(k, schema)}")
        else:
            lines.append("  args_required: []")
            lines.append("  args_schema: (none)")

        lines.append("")  # blank line between tools

    return "\n".join(lines).strip()