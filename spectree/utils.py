import functools
import inspect
import logging
import re
from hashlib import sha1
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    get_type_hints,
)

from ._pydantic import (
    BaseModel,
    ValidationError,
    generate_root_model,
    is_pydantic_model,
)
from ._types import (
    ModelType,
    MultiDict,
    MultiDictStarlette,
    NamingStrategy,
    NestedNamingStrategy,
    OptionalModelType,
)

# parse HTTP status code to get the code
HTTP_CODE = re.compile(r"^HTTP_(?P<code>\d{3})$")

RE_FLASK_RULE = re.compile(
    r"""
    (?P<static>[^<]*)                           # static rule data
    <
    (?:
        (?P<converter>[a-zA-Z_][a-zA-Z0-9_]*)   # converter name
        (?:\((?P<args>.*?)\))?                  # converter arguments
        \:                                      # variable delimiter
    )?
    (?P<variable>[a-zA-Z_][a-zA-Z0-9_]*)        # variable name
    >
    """,
    re.VERBOSE,
)

cached_type_hints = functools.cache(get_type_hints)

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
        docstring_parts[i] = docstring_parts[i].rstrip()
        docstring_parts[i] = docstring_parts[i].replace("\n", " ")

    summary = docstring_parts[0]
    description = None
    if len(docstring_parts) > 1:
        description = "\n\n".join(docstring_parts[1:])

    return summary, description


def parse_request(func: Any) -> Dict[str, Any]:
    """
    get json spec
    """
    content_items = {}
    if hasattr(func, "json"):
        content_items["application/json"] = {
            "schema": {"$ref": f"#/components/schemas/{func.json}"}
        }

    if hasattr(func, "form"):
        content_items["multipart/form-data"] = {
            "schema": {"$ref": f"#/components/schemas/{func.form}"}
        }

    if not content_items:
        return {}

    return {"content": content_items, "required": True}


def parse_params(
    func: Callable[..., Any],
    params: List[Mapping[str, Any]],
    models: Mapping[str, Any],
) -> List[Mapping[str, Any]]:
    """
    get spec for (query, headers, cookies)
    """
    attr_to_spec_key = {"query": "query", "headers": "header", "cookies": "cookie"}
    route_param_keywords = ("explode", "style", "allowReserved")

    for attr, position in attr_to_spec_key.items():
        if hasattr(func, attr):
            model = models[getattr(func, attr)]
            properties = model.get("properties", {model.get("title"): model})
            for name, schema in properties.items():
                # Route parameters keywords taken out of schema level
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


def has_model(func: Any) -> bool:
    """
    return True if this function have ``pydantic.BaseModel``
    """
    if any(hasattr(func, x) for x in ("query", "json", "headers")):
        return True

    return bool(hasattr(func, "resp") and func.resp.has_model())


def parse_code(http_code: str) -> str:
    """
    get the code of this HTTP status

    :param str http_code: format like ``HTTP_200``
    """
    match = HTTP_CODE.match(http_code)
    if not match:
        return ""
    return match.group("code")


def parse_name(func: Callable[..., Any]) -> str:
    """
    the func can be

        * undecorated functions
        * decorated functions
        * decorated class methods
    """
    return func.__name__


def default_before_handler(
    req: Any, resp: Any, req_validation_error: ValidationError, instance: Any
):
    """
    default handler called before the endpoint function after the request validation

    :param req: request provided by the web framework
    :param resp: response generated by SpecTree that will be returned
        if the validation error is not None
    :param req_validation_error: request validation error
    :param instance: class instance if the endpoint function is a class method
    """
    if req_validation_error:
        logger.error(
            "422 Request Validation Error: %s - %s",
            getattr(req_validation_error, "title", None)
            or req_validation_error.model.__name__,
            req_validation_error.errors(),
        )


def default_after_handler(
    req: Any, resp: Any, resp_validation_error: ValidationError, instance: Any
):
    """
    default handler called after the response validation

    :param req: request provided by the web framework
    :param resp: response from the endpoint function (if there is no validation error)
        or response validation error
    :param resp_validation_error: response validation error
    :param instance: class instance if the endpoint function is a class method
    """
    if resp_validation_error:
        logger.error(
            "500 Response Validation Error: %s - %s",
            getattr(resp_validation_error, "title", None)
            or resp_validation_error.model.__name__,
            resp_validation_error.errors(),
        )


def hash_module_path(module_path: str):
    """
    generate short hash for module path to avoid the
    same name object defined in different Python files

    :param module_path: `str` module path
    """

    return sha1(module_path.encode()).hexdigest()[:7]


def get_model_key(model: ModelType) -> str:
    """
    generate model name suffixed by short hashed path (instead of its path to
    avoid code-structure leaking)

    :param model: `pydantic.BaseModel` query, json, headers or cookies from
        request or response
    """

    return f"{model.__name__}.{hash_module_path(module_path=model.__module__)}"


def get_nested_key(parent: str, child: str) -> str:
    """
    generate nested model reference name suffixed by parent model name

    :param parent: string of parent name
    :param child: string of child name
    """

    return f"{parent}.{child}"


def get_model_schema(
    model: ModelType,
    naming_strategy: NamingStrategy = get_model_key,
    nested_naming_strategy: NestedNamingStrategy = get_nested_key,
):
    """
    return a dictionary representing the model as JSON Schema with a hashed
    infix in ref to ensure name uniqueness

    :param model: `pydantic.BaseModel` query, json, headers or cookies from
        request or response
    """
    assert is_pydantic_model(model), f"{model} is not a pydantic model"

    nested_key = nested_naming_strategy(naming_strategy(model), "{model}")
    return model.schema(ref_template=f"#/components/schemas/{nested_key}")


def get_security(security: Union[None, Mapping, Sequence[Any]]) -> List[Any]:
    """
    return the correct format of security
    """
    if security is None or not security:
        return []

    if isinstance(security, list):
        return security
    elif isinstance(security, dict):
        return [security]
    return []


def get_multidict_items(
    multidict: MultiDict, model: OptionalModelType = None
) -> Dict[str, Union[None, str, List[str]]]:
    """
    return the items of a :class:`werkzeug.datastructures.ImmutableMultiDict`
    """
    res: Dict[str, Union[None, str, List[str]]] = {}
    for key in multidict:
        values = multidict.getlist(key)
        if (model is not None and is_list_item(key, model)) or len(values) > 1:
            res[key] = multidict.getlist(key)
        else:
            res[key] = multidict.get(key)

    return res


def get_multidict_items_starlette(
    multidict: MultiDictStarlette, model: OptionalModelType = None
):
    """
    return the items of a :class:`starlette.datastructures.ImmutableMultiDict`
    """
    res = {}
    for key in multidict:
        values = multidict.getlist(key)
        if (model is not None and is_list_item(key, model)) or len(values) > 1:
            res[key] = multidict.getlist(key)
        else:
            res[key] = multidict[key]

    return res


def is_list_item(key: str, model: OptionalModelType) -> bool:
    """Check if this key is a list item in the model."""
    if model is None:
        return False
    model_filed = model.__fields__.get(key)
    if model_filed is None:
        return False
    return getattr(model_filed.annotation, "__origin__", None) is list


def gen_list_model(model: Type[BaseModel]) -> Type[BaseModel]:
    """
    Generate the corresponding list[model] class for a given model class.

    This only works for Pydantic V1. For V2, use `pydantic.RootModel` directly.
    """
    assert is_pydantic_model(model), f"{model} is not a pydantic model"
    return generate_root_model(List[model], name=f"{model.__name__}List")  # type: ignore


def werkzeug_parse_rule(
    rule: str,
) -> Iterator[Tuple[Optional[str], Optional[str], str]]:
    """A copy of werkzeug.parse_rule which is now removed.

    Parse a rule and return it as generator. Each iteration yields tuples
    in the form ``(converter, arguments, variable)``. If the converter is
    `None` it's a static url part, otherwise it's a dynamic one.
    """
    pos = 0
    end = len(rule)
    do_match = RE_FLASK_RULE.match
    used_names = set()
    while pos < end:
        m = do_match(rule, pos)
        if m is None:
            break
        data = m.groupdict()
        if data["static"]:
            yield None, None, data["static"]
        variable = data["variable"]
        converter = data["converter"] or "default"
        if variable in used_names:
            raise ValueError(f"variable name {variable!r} used twice.")
        used_names.add(variable)
        yield converter, data["args"] or None, variable
        pos = m.end()
    if pos < end:
        remaining = rule[pos:]
        if ">" in remaining or "<" in remaining:
            raise ValueError(f"malformed url rule: {rule!r}")
        yield None, None, remaining


def flask_response_unpack(resp: Any) -> Tuple[Any, int, List[Tuple[str, str]]]:
    """Parse Flask response object into a tuple of (payload, status_code, headers)."""
    status = 200
    headers: List[Tuple[str, str]] = []
    payload = None
    if not isinstance(resp, tuple):
        return resp, status, headers
    if len(resp) == 1:
        payload = resp[0]
    elif len(resp) == 2:
        payload = resp[0]
        if isinstance(resp[1], int):
            status = resp[1]
        else:
            headers = resp[1]
    elif len(resp) == 3:
        payload, status, headers = resp
    else:
        raise ValueError(
            f"Invalid return tuple: {resp}, expect (body,), (body, status), "
            "(body, headers), or (body, status, headers)."
        )
    return payload, status, headers


def parse_resp(func: Any, naming_strategy: NamingStrategy = get_model_key):
    """
    get the response spec

    If this function does not have explicit ``resp`` but have other models,
    a ``422 Validation Error`` will be appended to the response spec, since
    this may be triggered in the validation step.
    """
    responses = {}
    if hasattr(func, "resp"):
        responses = func.resp.generate_spec(naming_strategy)

    return responses
