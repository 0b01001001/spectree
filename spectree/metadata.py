import weakref
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FunctionDecorator:
    """Metadata associated with a validated endpoint."""

    query: str | None = None
    json: str | None = None
    form: str | None = None
    headers: str | None = None
    cookies: str | None = None
    resp: Any = None
    tags: Sequence[Any] = field(default_factory=tuple)
    security: dict | list[Any] | None = None
    deprecated: bool = False
    path_parameter_descriptions: Mapping[str, str] | None = None
    operation_id: str | None = None
    owner: Any = field(default=None, repr=False, compare=False)

    def parse_request(self) -> dict[str, Any]:
        content_items = {}
        if self.json is not None:
            content_items["application/json"] = {
                "schema": {"$ref": f"#/components/schemas/{self.json}"}
            }
        if self.form is not None:
            content_items["multipart/form-data"] = {
                "schema": {"$ref": f"#/components/schemas/{self.form}"}
            }
        return {"content": content_items, "required": True} if content_items else {}

    def parse_params(
        self, params: list[Mapping[str, Any]], models: Mapping[str, Any]
    ) -> list[Mapping[str, Any]]:
        attr_to_spec_key = {"query": "query", "headers": "header", "cookies": "cookie"}
        route_param_keywords = ("explode", "style", "allowReserved")
        for attr, position in attr_to_spec_key.items():
            model_key = getattr(self, attr)
            if model_key is None:
                continue
            model = models[model_key]
            properties = model.get("properties", {model.get("title"): model})
            for name, schema in properties.items():
                extra = {
                    kw: schema.pop(kw) for kw in route_param_keywords if kw in schema
                }
                params.append(
                    {
                        "name": name,
                        "in": position,
                        "schema": schema,
                        "required": name in model.get("required", []),
                        "description": schema.get("description", ""),
                        **extra,
                    }
                )
        return params

    def has_model(self) -> bool:
        return any(
            getattr(self, x) is not None for x in ("query", "json", "headers")
        ) or bool(self.resp and self.resp.has_model())

    def parse_resp(self, naming_strategy: Any) -> dict[str, Any]:
        return self.resp.generate_spec(naming_strategy) if self.resp else {}


_FUNCTION_METADATA: weakref.WeakKeyDictionary[Any, FunctionDecorator] = (
    weakref.WeakKeyDictionary()
)


def register_function_metadata(
    func: Any, owner: Any, metadata: FunctionDecorator
) -> None:
    """Associate validation metadata with a callable without mutating it."""
    metadata.owner = owner
    _FUNCTION_METADATA[func] = metadata


def get_function_metadata(func: Any) -> FunctionDecorator | None:
    """Return Spectree metadata for a callable, if it was validated."""
    func = getattr(func, "__func__", func)
    try:
        entry = _FUNCTION_METADATA.get(func)
    except TypeError:
        return None
    return entry


def get_function_owner(func: Any) -> Any:
    """Return the SpecTree instance that registered metadata for a callable."""
    func = getattr(func, "__func__", func)
    try:
        entry = _FUNCTION_METADATA.get(func)
    except TypeError:
        return None
    return entry.owner if entry is not None else None
