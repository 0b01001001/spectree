"""Fixture reproducing https://github.com/0b01001001/spectree/issues/312.

``ResponseValue`` is only imported while type checking, so the string forward
reference in ``view_func``'s return annotation cannot be evaluated at runtime.
This mirrors Flask's ``flask.typing.ResponseReturnValue`` (which references a
``TYPE_CHECKING``-only ``Response``) and would make ``typing.get_type_hints``
raise ``NameError`` even though spectree only needs the parameter annotations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.common import DemoModel

if TYPE_CHECKING:
    # Intentionally guarded so the name does not exist at runtime.
    from tests.common import DemoQuery as ResponseValue


def view_func(json: DemoModel) -> ResponseValue:
    # The body is never executed; only the annotations matter for this fixture.
    raise NotImplementedError
