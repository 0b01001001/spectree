"""Component schemas registered by one :class:`~spectree.spec.SpecTree`.

This module is an implementation detail of ``SpecTree``, not public API.
"""

from collections.abc import Callable, Iterator, Mapping
from typing import Any, NamedTuple

from spectree.model_adapter.protocol import SchemaMode
from spectree.utils import json_compatible_deepcopy

COMPONENT_REF_PREFIX = "#/components/schemas/"
SERIALIZATION_SUFFIX = "serialization"

NestedNamingStrategy = Callable[[str, str], str]


class _Component(NamedTuple):
    name: str
    validation: bool
    schema: dict[str, Any]
    definitions: dict[str, Any]


class SchemaRegistry:
    """Model schemas keyed by ``(component key, schema mode)``.

    Endpoints register their request models in ``validation`` mode and their
    response models in ``serialization`` mode when they are decorated.
    :meth:`render` builds the components of the OpenAPI document from the whole
    registry on every call and never modifies the stored schemas, so the
    document can be regenerated at any time.

    Component names are resolved from the complete registry, never from the
    registration order:

    - a key registered in one mode only, or in both modes with identical
      schemas, is published once, under the key itself;
    - when the validation and serialization schemas of one key differ, the
      validation schema keeps the key and the serialization schema is
      published as ``"<key>.serialization"``.

    Nested definitions (``$defs``) are published as separate components named
    by ``nested_naming_strategy(<final parent name>, <definition name>)``. When
    that strategy gives a validation and a serialization definition the same
    name but they differ (including the definitions they refer to), the
    validation definition keeps the name and the serialization one is
    published as ``"<name>.serialization"``.
    """

    def __init__(self) -> None:
        self._schemas: dict[tuple[str, SchemaMode], dict[str, Any]] = {}

    def register(self, key: str, mode: SchemaMode, schema: Mapping[str, Any]) -> None:
        """Store the schema that the model adapter generated for ``key`` in ``mode``.

        Registering the same key and mode again replaces the stored schema; this
        is what happens when the naming strategy maps two models to one key.
        """
        self._schemas[(key, mode)] = json_compatible_deepcopy(dict(schema))

    def component_name(self, key: str, mode: SchemaMode) -> str:
        """Return the name of the component that publishes ``key`` in ``mode``.

        The validation schema always keeps ``key`` itself, so request
        references can be built from the key directly.
        """
        if mode == "serialization" and self._modes_differ(key):
            return f"{key}.{SERIALIZATION_SUFFIX}"
        return key

    def render(
        self, nested_naming_strategy: NestedNamingStrategy
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Return new copies of the model components and of their nested definitions.

        ``components.schemas`` of the document is ``{**models, **definitions}``.
        """
        components = self._components()
        nested_names = self._nested_names(components, nested_naming_strategy)

        models: dict[str, Any] = {}
        definitions: dict[str, Any] = {}
        for component, names in zip(components, nested_names, strict=True):
            replacements = {
                f"{COMPONENT_REF_PREFIX}{child}": f"{COMPONENT_REF_PREFIX}{name}"
                for child, name in names.items()
            }
            _replace_refs(component.schema, replacements)
            _replace_refs(component.definitions, replacements)
            for child, definition in component.definitions.items():
                # As before, the first definition published under a name wins when
                # a custom nested naming strategy gives several definitions of one
                # mode the same name.
                definitions.setdefault(names[child], definition)
            models[component.name] = component.schema
        return models, definitions

    def _modes_differ(self, key: str) -> bool:
        validation = self._schemas.get((key, "validation"))
        serialization = self._schemas.get((key, "serialization"))
        return (
            validation is not None
            and serialization is not None
            and validation != serialization
        )

    def _components(self) -> list[_Component]:
        validation_names = {
            self.component_name(key, mode)
            for key, mode in self._schemas
            if mode == "validation"
        }
        components: list[_Component] = []
        names: set[str] = set()
        for (key, mode), stored in self._schemas.items():
            name = self.component_name(key, mode)
            if name in names:
                # Both modes produced the same schema and share one component.
                continue
            names.add(name)
            schema = json_compatible_deepcopy(stored)
            definitions = schema.pop("$defs", None)
            components.append(
                _Component(
                    name=name,
                    validation=name in validation_names,
                    schema=schema,
                    definitions=definitions if isinstance(definitions, dict) else {},
                )
            )
        return components

    @staticmethod
    def _nested_names(
        components: list[_Component], nested_naming_strategy: NestedNamingStrategy
    ) -> list[dict[str, str]]:
        """Name the nested definitions of every component before any is rewritten."""
        owners: dict[str, dict[str, Any]] = {}
        for component in components:
            if component.validation:
                for child in component.definitions:
                    owners.setdefault(
                        nested_naming_strategy(component.name, child),
                        _closure(component.definitions, child),
                    )

        nested_names = []
        for component in components:
            names = {}
            for child in component.definitions:
                name = nested_naming_strategy(component.name, child)
                owner = owners.get(name)
                if (
                    not component.validation
                    and owner is not None
                    and owner != _closure(component.definitions, child)
                ):
                    name = f"{name}.{SERIALIZATION_SUFFIX}"
                names[child] = name
            nested_names.append(names)
        return nested_names


def _iter_dicts(value: Any) -> Iterator[dict[str, Any]]:
    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            yield current
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)


def _closure(definitions: Mapping[str, Any], name: str) -> dict[str, Any]:
    """Return the definition ``name`` and the definitions it refers to, transitively."""
    closure: dict[str, Any] = {}
    pending = [name]
    while pending:
        current = pending.pop()
        if current in closure or current not in definitions:
            continue
        closure[current] = definitions[current]
        for node in _iter_dicts(definitions[current]):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith(COMPONENT_REF_PREFIX):
                pending.append(ref.removeprefix(COMPONENT_REF_PREFIX))
    return closure


def _replace_refs(value: Any, replacements: Mapping[str, str]) -> None:
    for node in _iter_dicts(value):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref in replacements:
            node["$ref"] = replacements[ref]
