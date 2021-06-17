from .base import BasePlugin
from .falcon_plugin import FalconAsgiPlugin, FalconPlugin
from .flask_plugin import FlaskPlugin
from .starlette_plugin import StarlettePlugin

PLUGINS = {
    "base": BasePlugin,
    "flask": FlaskPlugin,
    "falcon": FalconPlugin,
    "falcon-asgi": FalconAsgiPlugin,
    "starlette": StarlettePlugin,
}
