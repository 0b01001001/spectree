from .base import BasePlugin
from .flask_plugin import FlaskPlugin
from .falcon_plugin import FlaconPlugin
from .starlette_plugin import StarlettePlugin

PLUGINS = {
    'base': BasePlugin,
    'flask': FlaskPlugin,
    'falcon': FlaconPlugin,
    'starlette': StarlettePlugin,
}
