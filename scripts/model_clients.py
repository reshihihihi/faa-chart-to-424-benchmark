from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote


DEFAULT_OPENAI_BASE_URL = "http://127.0.0.1:8080/v1"
OPENAI_BASE_URL_ENVS = ["OPENAI_BASE_URL", "OPENAI_COMPAT_BASE_URL", "CODEX_PROXY_BASE_URL"]
OPENAI_API_KEY_ENVS = ["OPENAI_API_KEY", "OPENAI_COMPAT_API_KEY", "CODEX_PROXY_API_KEY"]


def _first_env(names: list[str]) -> tuple[str | None, str | None]:
    for name in names:
        value = os.environ.get(name)
        if value:
            return name, value
    return None, None


def _image_data_url(path: Path) -> str:
    media_type = "image/png"
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        media_type = "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{data}"


def _image_http_url(path: Path) -> str | None:
    root = os.environ.get("OPENAI_IMAGE_URL_ROOT")
    if not root:
        return None
    root_dir = Path(os.environ.get("OPENAI_IMAGE_URL_ROOT_DIR", os.getcwd())).resolve()
    resolved = path.resolve()
    try:
        rel = resolved.relative_to(root_dir)
    except ValueError:
        return None
    return root.rstrip("/") + "/" + quote(rel.as_posix(), safe="/")


def _use_openai_responses_api() -> bool:
    return os.environ.get("OPENAI_USE_RESPONSES_API", "").lower() in {"1", "true", "yes"}


def create_model_client(
    *,
    provider: str,
    base_url: str | None = None,
    api_key_env: str | None = None,
) -> Any:
    if provider == "anthropic_compatible":
        import anthropic

        auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        anthropic_base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL")
        if not auth_token and not api_key:
            raise RuntimeError("Missing ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY.")
        kwargs: dict[str, Any] = {}
        if auth_token:
            kwargs["auth_token"] = auth_token
        else:
            kwargs["api_key"] = api_key
        if anthropic_base_url:
            kwargs["base_url"] = anthropic_base_url
        return anthropic.Anthropic(**kwargs)

    if provider == "openai_compatible":
        from openai import OpenAI

        _, env_base_url = _first_env(OPENAI_BASE_URL_ENVS)
        resolved_base_url = base_url or env_base_url or DEFAULT_OPENAI_BASE_URL
        if api_key_env:
            api_key = os.environ.get(api_key_env)
            if not api_key:
                raise RuntimeError(f"Missing {api_key_env}.")
        else:
            _, api_key = _first_env(OPENAI_API_KEY_ENVS)
        return OpenAI(base_url=resolved_base_url, api_key=api_key or "local-proxy")

    raise ValueError(f"Unsupported provider: {provider}")


def model_api_manifest(
    *,
    provider: str,
    base_url: str | None = None,
    api_key_env: str | None = None,
    json_mode: bool = False,
    assistant_prefill_json: bool = False,
) -> dict[str, Any]:
    if provider == "openai_compatible":
        base_env, env_base_url = _first_env(OPENAI_BASE_URL_ENVS)
        resolved_base_url = base_url or env_base_url or DEFAULT_OPENAI_BASE_URL
        return {
            "provider": provider,
            "base_url": resolved_base_url,
            "base_url_env_candidates": OPENAI_BASE_URL_ENVS,
            "base_url_env_used": base_env,
            "auth_env_candidates": OPENAI_API_KEY_ENVS if api_key_env is None else [api_key_env],
            "token_value_recorded": False,
            "json_mode": json_mode,
            "assistant_prefill_json": assistant_prefill_json,
            "assistant_prefill_value": "{" if assistant_prefill_json else None,
            "openai_responses_api_enabled": _use_openai_responses_api(),
        }
    return {
        "provider": provider,
        "base_url_env": "ANTHROPIC_BASE_URL",
        "auth_env": "ANTHROPIC_AUTH_TOKEN",
        "token_value_recorded": False,
        "json_mode": json_mode,
        "assistant_prefill_json": assistant_prefill_json,
        "assistant_prefill_value": "{" if assistant_prefill_json else None,
        "tool_use_single_parameter_wrapper_unwrapped": True,
        "anthropic_tool_schema_transport_hardening": {
            "schema_metadata_keys_stripped_from_input_schema": ["$schema", "$id"],
            "tool_description_forbids_root_wrappers": True,
            "root_wrapper_normalization_enabled": False,
        },
    }


def normalize_tool_input(tool_input: Any) -> Any:
    if (
        isinstance(tool_input, dict)
        and set(tool_input.keys()) == {"parameter"}
        and isinstance(tool_input.get("parameter"), dict)
    ):
        return tool_input["parameter"]
    if isinstance(tool_input, dict) and len(tool_input) == 1:
        key = next(iter(tool_input.keys()))
        value = tool_input[key]
        if (
            key in {"$PARAMETER_NAME", "chart"}
            and isinstance(value, dict)
            and {"chart_id", "procedure", "missed_approach"}.issubset(value.keys())
        ):
            return value
    return tool_input


def anthropic_input_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a provider-facing schema without transport-level schema metadata."""

    def strip_metadata(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: strip_metadata(child)
                for key, child in value.items()
                if key not in {"$schema", "$id"}
            }
        if isinstance(value, list):
            return [strip_metadata(item) for item in value]
        return value

    return strip_metadata(schema)


def openai_responses_input_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a Responses API tool schema compatible with its stricter subset."""

    def convert(value: Any) -> Any:
        if isinstance(value, dict):
            converted = {}
            for key, child in value.items():
                if key in {"$schema", "$id"}:
                    continue
                converted["anyOf" if key == "oneOf" else key] = convert(child)
            if "const" in converted:
                const_value = converted.pop("const")
                converted.setdefault("enum", [const_value])
                if "type" not in converted:
                    if isinstance(const_value, str):
                        converted["type"] = "string"
                    elif isinstance(const_value, bool):
                        converted["type"] = "boolean"
                    elif isinstance(const_value, int):
                        converted["type"] = "integer"
                    elif isinstance(const_value, float):
                        converted["type"] = "number"
                    elif const_value is None:
                        converted["type"] = "null"
            return converted
        if isinstance(value, list):
            return [convert(item) for item in value]
        return value

    return convert(schema)


def call_model_json(
    client: Any,
    *,
    provider: str,
    model: str,
    prompt: str,
    image_path: Path | None,
    max_tokens: int,
    temperature: float,
    json_mode: bool,
    assistant_prefill_json: bool,
    output_control: str = "raw_json",
    tool_schema: dict[str, Any] | None = None,
    tool_name: str = "emit_canonical_json",
) -> tuple[str, Any]:
    if output_control == "openai_tool_call" and provider != "openai_compatible":
        raise ValueError("openai_tool_call output control requires provider=openai_compatible.")
    if output_control == "anthropic_tool_use" and provider != "anthropic_compatible":
        raise ValueError("anthropic_tool_use output control requires provider=anthropic_compatible.")
    if output_control in {"openai_tool_call", "anthropic_tool_use"} and tool_schema is None:
        raise ValueError(f"{output_control} output control requires tool_schema.")

    if provider == "anthropic_compatible":
        content: list[dict[str, Any]] = []
        if image_path is not None:
            data = base64.b64encode(image_path.read_bytes()).decode("ascii")
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": data,
                    },
                }
            )
        content.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content}]
        if assistant_prefill_json:
            if output_control == "anthropic_tool_use":
                raise ValueError("assistant_prefill_json is not compatible with anthropic_tool_use.")
            messages.append({"role": "assistant", "content": "{"})
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if output_control == "anthropic_tool_use":
            tool_description = (
                "Emit exactly one extraction object that follows the registered schema. "
                "The tool input itself must be the final JSON object. Its top-level keys "
                "must be the schema root keys, for canonical outputs exactly chart_id, "
                "procedure, and missed_approach. Do not wrap the object inside parameter, "
                "$PARAMETER_NAME, chart, output, result, arguments, or any other outer key."
            )
            kwargs["tools"] = [
                {
                    "name": tool_name,
                    "description": tool_description,
                    "input_schema": anthropic_input_schema(tool_schema),
                }
            ]
            kwargs["tool_choice"] = {"type": "tool", "name": tool_name}
        response = client.messages.create(**kwargs)
        if output_control == "anthropic_tool_use":
            tool_blocks = [
                block
                for block in response.content
                if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name
            ]
            if len(tool_blocks) != 1:
                raise RuntimeError(f"Expected exactly one Anthropic tool_use block, got {len(tool_blocks)}.")
            tool_input = normalize_tool_input(tool_blocks[0].input)
            return json.dumps(tool_input, ensure_ascii=False, separators=(",", ":")), response
        text_parts = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
        text = "\n".join(text_parts).strip()
        if assistant_prefill_json:
            text = ("{" + text).strip()
        return text, response

    if provider == "openai_compatible":
        content: list[dict[str, Any]] = []
        if image_path is not None:
            image_url = _image_http_url(image_path) or _image_data_url(image_path)
            content.append({"type": "image_url", "image_url": {"url": image_url}})
        content.append({"type": "text", "text": prompt})
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if output_control == "openai_tool_call":
            if _use_openai_responses_api():
                responses_content: list[dict[str, Any]] = []
                if image_path is not None:
                    responses_content.append({"type": "input_image", "image_url": _image_data_url(image_path)})
                responses_content.append({"type": "input_text", "text": prompt})
                response_kwargs: dict[str, Any] = {
                    "model": model,
                    "input": [{"role": "user", "content": responses_content}],
                    "tools": [
                        {
                            "type": "function",
                            "name": tool_name,
                            "description": "Emit one extraction output object that follows the registered schema.",
                            "parameters": openai_responses_input_schema(tool_schema),
                            "strict": True,
                        }
                    ],
                    "tool_choice": {"type": "function", "name": tool_name},
                    "max_output_tokens": max_tokens,
                }
                argument_chunks: list[str] = []
                completed_arguments = ""
                with client.responses.stream(**response_kwargs) as stream:
                    for event in stream:
                        event_type = getattr(event, "type", "")
                        if event_type == "response.function_call_arguments.delta":
                            argument_chunks.append(getattr(event, "delta", ""))
                        elif event_type == "response.function_call_arguments.done":
                            completed_arguments = getattr(event, "arguments", "") or ""
                    response = stream.get_final_response()
                text = completed_arguments or "".join(argument_chunks)
                if not text:
                    raise RuntimeError("Expected streamed function call arguments from OpenAI Responses API, got none.")
                return text.strip(), response
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": "Emit one extraction output object that follows the registered schema.",
                        "parameters": tool_schema,
                        "strict": True,
                    },
                }
            ]
            kwargs["tool_choice"] = {"type": "function", "function": {"name": tool_name}}
        elif json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        message_content = response.choices[0].message.content
        if output_control == "openai_tool_call":
            tool_calls = response.choices[0].message.tool_calls or []
            if len(tool_calls) != 1:
                raise RuntimeError(f"Expected exactly one tool call, got {len(tool_calls)}.")
            call = tool_calls[0]
            if call.function.name != tool_name:
                raise RuntimeError(f"Expected tool call {tool_name}, got {call.function.name}.")
            return call.function.arguments.strip(), response
        if isinstance(message_content, list):
            text = "".join(
                part.get("text", "") if isinstance(part, dict) else getattr(part, "text", "")
                for part in message_content
            )
        else:
            text = message_content or ""
        return text.strip(), response

    raise ValueError(f"Unsupported provider: {provider}")


def save_model_response(path: Path, response: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(response, "model_dump_json"):
        path.write_text(response.model_dump_json(indent=2), encoding="utf-8")
    elif hasattr(response, "to_json"):
        path.write_text(response.to_json(), encoding="utf-8")
    else:
        path.write_text(json.dumps(response, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
