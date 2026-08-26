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
            for name, property_schema in properties.items():
                schema = property_schema.copy()
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


_VALIDATED_FUNCTIONS: weakref.WeakSet[Any] = weakref.WeakSet()


def iter_wrapped_functions(func: Any):
    """Yield a callable and its bound-method/``__wrapped__`` chain."""
    seen: set[int] = set()
    current = func
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        current = getattr(current, "__func__", current)
        yield current
        current = getattr(current, "__wrapped__", None)


def register_validated_function(func: Any) -> None:
    """Record a callable as having been validated by a ``SpecTree`` instance."""
    _VALIDATED_FUNCTIONS.add(func)


def is_validated_function(func: Any) -> bool:
    """Return whether a callable was validated by any ``SpecTree`` instance."""
    for candidate in iter_wrapped_functions(func):
        try:
            if candidate in _VALIDATED_FUNCTIONS:
                return True
        except TypeError:
            continue
    return False
