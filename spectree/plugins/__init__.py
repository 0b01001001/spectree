from .base import BasePlugin
from .falcon_plugin import FalconAsgiPlugin, FalconPlugin
from .flask_plugin import FlaskPlugin
from .starlette_plugin import StarlettePlugin
from .quart_plugin import QuartPlugin

PLUGINS = {
    "base": BasePlugin,
    "flask": FlaskPlugin,
    "quart": QuartPlugin,
    "falcon": FalconPlugin,
    "falcon-asgi": FalconAsgiPlugin,
    "starlette": StarlettePlugin,
}
