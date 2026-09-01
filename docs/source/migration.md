# Migrating from Spectree v2 to v3

Spectree v3 introduces a model-adapter layer. Pydantic remains the default
backend, while msgspec and plain dataclasses are now supported through the same
validation and OpenAPI generation contract.

## Installation now requires a model extra

Pydantic is no longer an unconditional dependency. Existing Pydantic users
should install the `pydantic` extra:

```bash
pip install "spectree[pydantic]"
```

To use msgspec instead:

```bash
pip install "spectree[msgspec]"
```

`SpecTree` continues to select Pydantic when no adapter is passed. A bare
`pip install spectree` is therefore intended for applications that supply their
own model adapter; it is not sufficient to construct the default `SpecTree`.

## Select the model adapter explicitly

Existing Pydantic applications can continue to rely on the default:

```python
from spectree import SpecTree

api = SpecTree("flask")
```

Applications using msgspec must pass its adapter:

```python
from spectree import SpecTree, get_msgspec_model_adapter

api = SpecTree("falcon", model_adapter=get_msgspec_model_adapter())
```

Custom adapters must implement the
[`ModelAdapter`](https://github.com/0b01001001/spectree/blob/main/spectree/model_adapter/protocol.py)
protocol.

## File models come from the active adapter

The old top-level `spectree.BaseFile` type has been replaced by the active
adapter's `basefile` contract. This lets each model backend expose the file type
it can validate:

```python
from pydantic import BaseModel
from spectree import get_pydantic_model_adapter

model_adapter = get_pydantic_model_adapter()


class UploadForm(BaseModel):
    file: model_adapter.basefile
```

Pass the same adapter to `SpecTree` when selecting it explicitly.

## Hooks receive the active adapter

The `before` and `after` hook signatures have a new final argument:

```python
def before(request, response, validation_error, instance, model_adapter):
    ...


def after(request, response, validation_error, instance, model_adapter):
    ...
```

Update custom hooks that accepted exactly four arguments. The new argument
provides adapter-specific validation errors, serialization, and schema behavior.

## Spectree metadata models are no longer Pydantic models

Spectree's configuration and OpenAPI metadata classes now use adapter-backed
dataclasses rather than inheriting from `pydantic.BaseModel`. This affects code
that directly manipulates classes such as `Configuration`,
`SecuritySchemeData`, `SecurityScheme`, `Server`, `Tag`, or `ExternalDocs`.

- Use `.to_dict()` instead of Pydantic's `.model_dump()`.
- Plain construction still works for already-typed values.
- When validating mappings, call `.model_validate()` with the active adapter:

```python
from spectree import get_pydantic_model_adapter
from spectree.models import SecuritySchemeData

model_adapter = get_pydantic_model_adapter()
scheme = SecuritySchemeData.model_validate(
    {"type": "apiKey", "name": "X-API-Key", "in": "header"},
    model_adapter=model_adapter,
)
```

## Model names may change

The default naming strategy now handles wrapped model types such as
`Annotated[Item, ...]` and `list[Item]`. This can change generated component
keys for applications that depended on the previous names.

Use `naming_strategy` and `nested_naming_strategy` on `SpecTree` when component
names are part of a published OpenAPI contract:

```python
api = SpecTree(
    "flask",
    naming_strategy=lambda model: model.__name__.lower(),
    nested_naming_strategy=lambda _parent, child: child,
)
```

## Validation errors are adapter-specific

Validation exceptions and their serialized details now come from the active
model adapter. Code in custom hooks or plugins should use
`model_adapter.validation_error` and `model_adapter.validation_errors(error)`
instead of assuming a Pydantic `ValidationError`.

## Upgrade checklist

1. Install `spectree[pydantic]` or `spectree[msgspec]`.
2. Pass a non-default model adapter to `SpecTree`.
3. Update hook functions to accept `model_adapter`.
4. Replace direct `spectree.BaseFile` use with `model_adapter.basefile`.
5. Replace Pydantic-only operations on Spectree metadata classes.
6. Compare the generated OpenAPI document, especially component names and
   serialized response schemas, before deploying.
