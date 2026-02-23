import json


class AstValidationError(Exception):
    pass


def _is_type(value, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    return False


def ast_validate_tool_call(raw_output: str, tools_by_id: dict, visible_tool_ids: list) -> dict:
    """
    Stage 1: AST validation = output correctness.

    Checks:
    - valid JSON object
    - exactly {tool_id, arguments}
    - tool_id exists AND is visible/allowed
    - required args present
    - no extra args
    - type checks (+ enum/min/max)
    """
    if raw_output is None:
        raise AstValidationError("raw_output is None")

    text = raw_output.strip()
    if not text:
        raise AstValidationError("Empty model output")

    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        raise AstValidationError(f"Invalid JSON: {e}") from e

    if not isinstance(obj, dict):
        raise AstValidationError("Tool call must be a JSON object")

    allowed_top_keys = {"tool_id", "arguments"}
    missing_top = allowed_top_keys - set(obj.keys())
    extra_top = set(obj.keys()) - allowed_top_keys

    if missing_top:
        raise AstValidationError(f"Missing top-level keys: {sorted(list(missing_top))}")
    if extra_top:
        raise AstValidationError(f"Unexpected top-level keys: {sorted(list(extra_top))}")

    tool_id = obj["tool_id"]
    arguments = obj["arguments"]

    if not isinstance(tool_id, str) or not tool_id.strip():
        raise AstValidationError("tool_id must be a non-empty string")

    if not isinstance(arguments, dict):
        raise AstValidationError("arguments must be a JSON object")

    # tool must exist in database
    if tool_id not in tools_by_id:
        raise AstValidationError(f"Unknown tool_id '{tool_id}'")

    # tool must be visible/allowed in this run
    visible_set = set(visible_tool_ids or [])
    if tool_id not in visible_set:
        raise AstValidationError(f"Tool '{tool_id}' is not visible/allowed in this context")

    tool = tools_by_id[tool_id]
    args_schema = tool.get("args", {})
    props = args_schema.get("properties", {})
    required = args_schema.get("required", [])

    if not isinstance(props, dict) or not isinstance(required, list):
        raise AstValidationError(f"Tool '{tool_id}' has invalid args schema")

    allowed_arg_keys = set(props.keys())
    given_arg_keys = set(arguments.keys())

    # required present
    missing_args = [k for k in required if k not in given_arg_keys]
    if missing_args:
        raise AstValidationError(f"Missing required argument(s): {missing_args}")

    # no extra args
    extra_args = sorted(list(given_arg_keys - allowed_arg_keys))
    if extra_args:
        raise AstValidationError(f"Unexpected argument(s): {extra_args}")

    # type + enum + min/max checks
    for key, spec in props.items():
        if key not in arguments:
            continue  # optional arg omitted
        val = arguments[key]

        if not isinstance(spec, dict):
            raise AstValidationError(f"Invalid schema for argument '{key}'")

        expected_type = spec.get("type")
        if expected_type and not _is_type(val, expected_type):
            raise AstValidationError(f"Argument '{key}' has wrong type. Expected {expected_type}.")

        if "enum" in spec:
            enum_vals = spec["enum"]
            if isinstance(enum_vals, list) and val not in enum_vals:
                raise AstValidationError(f"Argument '{key}' must be one of {enum_vals}")

        if isinstance(val, (int, float)) and not isinstance(val, bool):
            if "minimum" in spec and val < spec["minimum"]:
                raise AstValidationError(f"Argument '{key}' must be >= {spec['minimum']}")
            if "maximum" in spec and val > spec["maximum"]:
                raise AstValidationError(f"Argument '{key}' must be <= {spec['maximum']}")

    return {"tool_id": tool_id, "arguments": arguments}