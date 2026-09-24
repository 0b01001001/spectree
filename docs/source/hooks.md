# Hooks

SpecTree provides `before` and `after` hooks so you can customize what happens
around validation — for example, recording metrics, logging validation errors,
or building a custom error response.

## Signatures

```{note}
The `model_adapter` argument was added in SpecTree v3. Hooks written for v2
accepted only four arguments. See the [migration guide](migration.md) for
details.
```

Both hooks receive five positional arguments:

```python
def before(req, resp, req_validation_error, instance, model_adapter):
    ...


def after(req, resp, resp_validation_error, instance, model_adapter):
    ...
```

- `req`: the request object provided by the web framework
- `resp`: for `before`, the response SpecTree will return if request validation
  failed; for `after`, the response from the endpoint function
- `req_validation_error` / `resp_validation_error`: the validation error, or
  `None` if validation passed
- `instance`: the class instance when the endpoint is a class method, otherwise
  `None`
- `model_adapter`: the model adapter used by the current `SpecTree` instance,
  giving access to adapter-specific error details and serialization

## When the hooks run

- `before` runs after request validation and before the endpoint function. If
  request validation failed, the endpoint is skipped and the `resp` argument is
  the error response SpecTree generated.
- `after` runs after the endpoint function and response validation.

## Setting hooks

Hooks can be set globally on the `SpecTree` instance:

```python
from spectree import SpecTree


def custom_before(req, resp, req_validation_error, instance, model_adapter):
    if req_validation_error:
        resp.status = 400
        resp.media = {"errors": model_adapter.validation_errors(req_validation_error)}


spec = SpecTree("falcon", before=custom_before)
```

or per endpoint through `validate`:

```python
@spec.validate(query=Query, before=custom_before)
def handler():
    ...
```

If you don't provide hooks, SpecTree uses
{func}`spectree.utils.default_before_handler` and
{func}`spectree.utils.default_after_handler`, which log validation errors.
