from .base import BasePlugin
from .flask_plugin import FlaskPlugin
from .falcon_plugin import FlaconPlugin

PLUGINS = {
    'base': BasePlugin,
    'flask': FlaskPlugin,
    'falcon': FlaconPlugin,
}
