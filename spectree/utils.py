import inspect
import logging
import re
from hashlib import sha1
from typing import Any, Callable, Optional, Tuple, Type

from pydantic import BaseModel

# parse HTTP status code to get the code
HTTP_CODE = re.compile(r"^HTTP_(?P<code>\d{3})$")

logger = logging.getLogger(__name__)


def parse_comments(func: Callable[..., Any]) -> Tuple[Optional[str], Optional[str]]:
    """Parse function docstring into a summary and description string.

    The first few lines of the docstring up to the first empty line will be extracted
    as the summary, and the rest of the docstring, following the empty line will become
    the description.

    If the function's docstring also contains parameter documentation, you can avoid
    parsing it as part of the summary or description by prefixing it with the `"\\\\f"`
    form feed character. Everything after the `"\\\\f"` character will be ignored in the
    docstring.

    :param func: The callable whose docstring should be parsed.
    :returns: A two element tuple with the summary and the description strings.
    """
    docstring = inspect.getdoc(func)
    if docstring is None:
        return None, None

    docstring = re.split("\f", docstring, maxsplit=1)[0]

    docstring_parts = re.split(r"\n\s*\n", docstring)
    for i in range(len(docstring_parts)):
        docstring_parts[i] = docstring_parts[i].replace("\n", " ")

    summary = docstring_parts[0]
    description = None
    if len(docstring_parts) > 1:
        description = "\n\n".join(docstring_parts[1:])

    return summary, description


def parse_request(func):
    """
    get json spec
    """
    data = {}
    if hasattr(func, "json"):
        data = {
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{func.json}"}
                }
            }
        }
    return data


def parse_params(func, params, models):
    """
    get spec for (query, headers, cookies)
    """
    attr_to_spec_key = {"query": "query", "headers": "header", "cookies": "cookie"}
    route_param_keywords = ("explode", "style", "allowReserved")

    for attr in attr_to_spec_key:
        if hasattr(func, attr):
            model = models[getattr(func, attr)]
            for name, schema in model["properties"].items():
                # Route parameters keywords taken out of schema level
                extra = {
                    kw: schema.pop(kw) for kw in route_param_keywords if kw in schema
                }
                params.append(
                    {
                        "name": name,
                        "in": attr_to_spec_key[attr],
                        "schema": schema,
                        "required": name in model.get("required", []),
                        "description": schema.get("description", ""),
                        **extra,
                    }
                )

    return params


def parse_resp(func):
    """
    get the response spec

    If this function does not have explicit ``resp`` but have other models,
    a ``422 Validation Error`` will be append to the response spec. Since
    this may be triggered in the validation step.
    """
    responses = {}
    if hasattr(func, "resp"):
        responses = func.resp.generate_spec()

    return responses


def has_model(func):
    """
    return True if this function have ``pydantic.BaseModel``
    """
    if any(hasattr(func, x) for x in ("query", "json", "headers")):
        return True

    return bool(hasattr(func, "resp") and func.resp.has_model())


def parse_code(http_code):
    """
    get the code of this HTTP status

    :param str http_code: format like ``HTTP_200``
    """
    match = HTTP_CODE.match(http_code)
    if not match:
        return None
    return match.group("code")


def parse_name(func):
    """
    the func can be

        * undecorated functions
        * decorated functions
        * decorated class methods
    """
    return func.__name__


def default_before_handler(req, resp, req_validation_error, instance):
    """
    default handler called before the endpoint function after the request validation

    :param req: request provided by the web framework
    :param resp: response generated by SpecTree that will be returned
        if the validation error is not None
    :param req_validation_error: request validation error
    :param instance: class instance if the endpoint function is a class method
    """
    if req_validation_error:
        logger.info(
            "422 Validation Error",
            extra={
                "spectree_model": req_validation_error.model.__name__,
                "spectree_validation": req_validation_error.errors(),
            },
        )


def default_after_handler(req, resp, resp_validation_error, instance):
    """
    default handler called after the response validation

    :param req: request provided by the web framework
    :param resp: response from the endpoint function (if there is no validation error)
        or response validation error
    :param resp_validation_error: response validation error
    :param instance: class instance if the endpoint function is a class method
    """
    if resp_validation_error:
        logger.info(
            "500 Response Validation Error",
            extra={
                "spectree_model": resp_validation_error.model.__name__,
                "spectree_validation": resp_validation_error.errors(),
            },
        )


def hash_module_path(module_path: str):
    """
    generate short hashed prefix for module path

    :param modelpath: `str` module path
    """

    return sha1(module_path.encode()).hexdigest()[:7]


def get_model_path_key(model_path: str):
    """
    generate short hashed prefix for module path (instead of its path to avoid
    code-structure leaking)

    :param modelpath: `str` model path in string
    """

    model_path_parts = model_path.rsplit(".", 1)
    if len(model_path_parts) > 1:
        hashed_module_path = hash_module_path(module_path=model_path_parts[0])
        model_path_key = f"{hashed_module_path}.{model_path_parts[1]}"
    else:
        model_path_key = model_path_parts[0]

    return model_path_key


def get_model_key(model: Type[BaseModel]) -> str:
    """
    generate model name prefixed by short hashed path (instead of its path to
    avoid code-structure leaking)

    :param model: `pydantic.BaseModel` query, json, headers or cookies from
    request or response
    """

    return f"{hash_module_path(module_path=model.__module__)}.{model.__name__}"


def get_model_schema(model):
    """
    return a dictionary representing the model as JSON Schema with using hashed
    prefix in ref

    :param model: `pydantic.BaseModel` query, json, headers or cookies from
    request or response
    """
    assert issubclass(model, BaseModel)

    return model.schema(
        ref_template=f"#/components/schemas/{get_model_key(model)}.{{model}}"
    )


def get_security(security):
    """
    return the correct format of security
    """
    if security is None or not security:
        return []

    if isinstance(security, dict):
        security = [security]

    return security
