from .base import BasePlugin
from .falcon_plugin import FalconPlugin
from .flask_plugin import FlaskPlugin
from .starlette_plugin import StarlettePlugin

PLUGINS = {
    "base": BasePlugin,
    "flask": FlaskPlugin,
    "falcon": FalconPlugin,
    "starlette": StarlettePlugin,
}
