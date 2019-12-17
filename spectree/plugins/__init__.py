from .web_flask import FlaskPlugin
from .web_falcon import FlaconPlugin

PLUGINS = {
    'flask': FlaskPlugin,
    'falcon': FlaconPlugin,
}
