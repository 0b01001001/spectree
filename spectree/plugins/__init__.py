from .base import BasePlugin
from .flask_plugin import FlaskPlugin
from .falcon_plugin import FalconPlugin
from .starlette_plugin import StarlettePlugin

PLUGINS = {
    'base': BasePlugin,
    'flask': FlaskPlugin,
    'falcon': FalconPlugin,
    'starlette': StarlettePlugin,
}
