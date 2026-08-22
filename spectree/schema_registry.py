from dataclasses import dataclass
from typing import Any, Iterator, Mapping

from spectree.model_adapter.protocol import SchemaMode
from spectree.utils import json_compatible_deepcopy


class SchemaCollisionError(ValueError):
    """Raised when two incompatible schemas resolve to the same component name."""


@dataclass(frozen=True, slots=True)
class SchemaRecord:
    model: Any
    mode: SchemaMode
    component_name: str
    raw_schema: dict[str, Any]
    schema: dict[str, Any]


class SchemaRegistry(Mapping[str, dict[str, Any]]):
    """
    Registry of OpenAPI component schemas.

    A schema identity is based on:
        (naming_strategy(model), schema mode)

    Validation and serialization schemas may share the same component when
    they are identical. If they differ, the later registration gets a
    mode-specific component suffix.
    """

    def __init__(
        self,
        naming_strategy,
        nested_naming_strategy,
    ) -> None:
        self.naming_strategy = naming_strategy
        self.nested_naming_strategy = nested_naming_strategy

        self._schemas: dict[str, dict[str, Any]] = {}
        self._records: dict[tuple[str, SchemaMode], SchemaRecord] = {}

    def __getitem__(self, name: str) -> dict[str, Any]:
        return self._schemas[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._schemas)

    def __len__(self) -> int:
        return len(self._schemas)

    def register(
        self,
        model: Any,
        mode: SchemaMode,
        schema: dict[str, Any],
    ) -> str:
        """
        Register a model schema and return its final OpenAPI component name.
        """
        base_name = self.naming_strategy(model)
        identity = (base_name, mode)

        raw_schema = json_compatible_deepcopy(schema)

        existing = self._records.get(identity)
        if existing is not None:
            normalized = self._normalize_schema(
                raw_schema,
                existing.component_name,
            )

            if existing.model is not model:
                raise SchemaCollisionError(
                    f"Schema name collision for {base_name!r}: "
                    f"multiple models use the same name for {mode!r} schema."
                )

            if existing.schema != normalized:
                raise SchemaCollisionError(
                    f"Schema for {base_name!r} in {mode!r} mode "
                    "changed after registration."
                )

            return existing.component_name

        other_mode = self._other_mode(mode)
        other = self._records.get((base_name, other_mode))

        if other is not None:
            if other.model is not model:
                raise SchemaCollisionError(
                    f"Schema name collision for {base_name!r}: "
                    "different models use the same component name."
                )

            if other.raw_schema == raw_schema:
                self._records[identity] = SchemaRecord(
                    model=model,
                    mode=mode,
                    component_name=other.component_name,
                    raw_schema=raw_schema,
                    schema=other.schema,
                )
                return other.component_name

            component_name = f"{base_name}.{mode}"

            if component_name in self._schemas:
                raise SchemaCollisionError(
                    f"Cannot register {base_name!r} {mode!r} schema: "
                    f"component {component_name!r} already exists."
                )
        else:
            component_name = base_name

            if component_name in self._schemas:
                raise SchemaCollisionError(
                    f"Schema component {component_name!r} already exists."
                )

        normalized = self._normalize_schema(
            raw_schema,
            component_name,
        )

        self._schemas[component_name] = normalized
        self._records[identity] = SchemaRecord(
            model=model,
            mode=mode,
            component_name=component_name,
            raw_schema=raw_schema,
            schema=normalized,
        )

        return component_name

    @staticmethod
    def _other_mode(mode: SchemaMode) -> SchemaMode:
        return (
            "serialization"
            if mode == "validation"
            else "validation"
        )

    def _normalize_schema(
        self,
        schema: dict[str, Any],
        component_name: str,
    ) -> dict[str, Any]:
        """
        Rewrite adapter-local nested $defs references to their final
        OpenAPI component names.
        """
        definitions = schema.get("$defs")

        if not isinstance(definitions, dict):
            return schema

        replacements = {
            f"#/components/schemas/{key}": (
                "#/components/schemas/"
                f"{self.nested_naming_strategy(component_name, key)}"
            )
            for key in definitions
        }

        values: list[Any] = [schema]

        while values:
            value = values.pop()

            if isinstance(value, dict):
                ref = value.get("$ref")

                if isinstance(ref, str) and ref in replacements:
                    value["$ref"] = replacements[ref]

                values.extend(value.values())

            elif isinstance(value, list):
                values.extend(value)

        return schema
