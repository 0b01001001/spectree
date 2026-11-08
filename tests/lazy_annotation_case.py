"""A handler whose annotations are evaluated lazily (PEP 649, Python 3.14+).

Without ``from __future__ import annotations``, ``ResponseValue`` exists only for
type checkers. Before Python 3.14 this module cannot be imported at all; on 3.14
reading ``view.__annotations__`` raises ``NameError``, although Spectree only
needs the ``json`` annotation.
"""

from typing import TYPE_CHECKING

from tests.common_dataclass import DemoModel

if TYPE_CHECKING:
    from tests.common import DemoQuery as ResponseValue


def view(json: DemoModel) -> ResponseValue:
    return {"name": json.name}  # type: ignore[return-value]
