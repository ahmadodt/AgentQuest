import json
from typing import Any

from src.prompts.tool_renderers.compact_tools import render_tools_compact


def resolve_tool_for_display(gamedata: dict, tool: dict[str, Any]) -> dict[str, Any]:
    llm_tools_by_id = gamedata.get("llm_tools_by_id", {})
    return llm_tools_by_id.get(tool.get("tool_id"), tool)


def build_human_tool_call(
    *,
    form_key: str,
    tool: dict[str, Any],
) -> dict[str, Any]:
    import streamlit as st

    arguments: dict[str, Any] = {}
    args_schema = tool.get("args", {}) or {}
    properties = args_schema.get("properties", {}) or {}
    required = set(args_schema.get("required", []) or [])

    for arg_name, schema in properties.items():
        field_key = f"{form_key}_{tool.get('tool_id')}_{arg_name}"
        arg_type = schema.get("type", "string")
        value: Any

        if isinstance(schema.get("enum"), list) and schema["enum"]:
            value = st.selectbox(
                f"{arg_name}{' *' if arg_name in required else ''}",
                schema["enum"],
                key=field_key,
            )
        elif arg_type == "boolean":
            value = st.checkbox(arg_name, key=field_key)
        elif arg_type == "integer":
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            default_value = minimum if isinstance(minimum, int) else 0
            input_label = f"{arg_name}{' *' if arg_name in required else ''}"
            if isinstance(minimum, int) and isinstance(maximum, int):
                value = st.number_input(input_label, min_value=minimum, max_value=maximum, value=default_value, step=1, key=field_key)
            elif isinstance(minimum, int):
                value = st.number_input(input_label, min_value=minimum, value=default_value, step=1, key=field_key)
            elif isinstance(maximum, int):
                value = st.number_input(input_label, max_value=maximum, value=min(default_value, maximum), step=1, key=field_key)
            else:
                value = st.number_input(input_label, value=default_value, step=1, key=field_key)
        elif arg_type == "number":
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            default_value = float(minimum) if isinstance(minimum, (int, float)) else 0.0
            input_label = f"{arg_name}{' *' if arg_name in required else ''}"
            if isinstance(minimum, (int, float)) and isinstance(maximum, (int, float)):
                value = st.number_input(input_label, min_value=float(minimum), max_value=float(maximum), value=default_value, key=field_key)
            elif isinstance(minimum, (int, float)):
                value = st.number_input(input_label, min_value=float(minimum), value=default_value, key=field_key)
            elif isinstance(maximum, (int, float)):
                value = st.number_input(input_label, max_value=float(maximum), value=min(default_value, float(maximum)), key=field_key)
            else:
                value = st.number_input(input_label, value=default_value, key=field_key)
        elif arg_type in {"object", "array"}:
            raw_json = st.text_area(
                f"{arg_name}{' *' if arg_name in required else ''} (JSON)",
                value="{}" if arg_type == "object" else "[]",
                key=field_key,
            )
            if raw_json.strip():
                value = raw_json
            else:
                value = None
        else:
            value = st.text_input(
                f"{arg_name}{' *' if arg_name in required else ''}",
                key=field_key,
            )

        if arg_type in {"object", "array"}:
            if value is None or (isinstance(value, str) and not value.strip()):
                if arg_name in required:
                    arguments[arg_name] = value
                continue
            arguments[arg_name] = value
            continue

        if arg_name in required or value not in ("", None):
            arguments[arg_name] = value

    return arguments


def parse_human_arguments(
    *,
    tool: dict[str, Any],
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    parsed_arguments: dict[str, Any] = {}
    properties = ((tool.get("args", {}) or {}).get("properties", {}) or {})
    for arg_name, value in arguments.items():
        schema = properties.get(arg_name, {})
        arg_type = schema.get("type")
        if arg_type in {"object", "array"} and isinstance(value, str):
            try:
                parsed_arguments[arg_name] = json.loads(value)
            except Exception:
                return {}, f"Argument '{arg_name}' must be valid JSON."
        else:
            parsed_arguments[arg_name] = value
    return parsed_arguments, None


def render_human_tool_panel(
    *,
    gamedata: dict,
    run_settings: dict[str, Any],
    scene_context: dict[str, Any],
    submit_label: str,
    form_key: str,
) -> str | None:
    import streamlit as st

    cfg = run_settings["preset_config"]
    visible_tools = scene_context["visible_tools"]
    tool_labels = {
        tool["tool_id"]: f"{tool.get('label') or tool['tool_id']} ({tool['tool_id']})"
        for tool in visible_tools
    }
    selected_tool_key = f"{form_key}_selected_tool"
    selected_tool_id = st.session_state.get(selected_tool_key) or next(iter(tool_labels))

    st.subheader("Choose a Tool")
    tool_cols = st.columns(min(3, len(visible_tools)) or 1)
    for index, visible_tool in enumerate(visible_tools):
        display_tool = resolve_tool_for_display(gamedata, visible_tool)
        with tool_cols[index % len(tool_cols)]:
            with st.container(border=True):
                st.markdown(f"**{visible_tool.get('label') or visible_tool['tool_id']}**")
                st.caption(visible_tool["tool_id"])
                with st.expander("Tool details", expanded=visible_tool["tool_id"] == selected_tool_id):
                    st.code(render_tools_compact([display_tool], cfg), language="text")

    selected_tool_id = st.selectbox(
        "Selected tool",
        list(tool_labels.keys()),
        format_func=lambda item: tool_labels[item],
        key=selected_tool_key,
    )
    selected_tool = next(tool for tool in visible_tools if tool["tool_id"] == selected_tool_id)
    with st.form(key=f"{form_key}_tool_form"):
        st.caption("Required fields are marked with *.")
        raw_arguments = build_human_tool_call(form_key=form_key, tool=selected_tool)
        submitted = st.form_submit_button(submit_label)

    if not submitted:
        return None

    parsed_arguments, argument_error = parse_human_arguments(tool=selected_tool, arguments=raw_arguments)
    if argument_error:
        st.error(argument_error)
        return None

    return json.dumps(
        {
            "tool_id": selected_tool_id,
            "arguments": parsed_arguments,
        },
        ensure_ascii=False,
    )
