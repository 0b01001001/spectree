from collections import namedtuple

from .base import BasePlugin

__all__ = ["BasePlugin"]

Plugin = namedtuple("Plugin", ("name", "package", "class_name"))

PLUGINS = {
    "base": Plugin(".base", __name__, "BasePlugin"),
    "flask": Plugin(".flask_plugin", __name__, "FlaskPlugin"),
    "falcon": Plugin(".falcon_plugin", __name__, "FalconPlugin"),
    "falcon-asgi": Plugin(".falcon_plugin", __name__, "FalconAsgiPlugin"),
    "starlette": Plugin(".starlette_plugin", __name__, "StarlettePlugin"),
}
