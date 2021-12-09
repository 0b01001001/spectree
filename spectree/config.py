import logging
from typing import List, Optional

from .models import SecurityScheme, Server
from .page import DEFAULT_PAGE_TEMPLATES


class Config:
    """
    :ivar MODE: mode for route. **normal** includes undecorated routes and
        routes decorated by this instance. **strict** only includes routes
        decorated by this instance. **greedy** includes all the routes.
    :ivar PATH: path for API document page
    :ivar OPENAPI_VERSION: OpenAPI version
    :ivar TITLE: service name
    :ivar VERSION: service version
    :ivar DOMAIN: service host domain
    :ivar SECURITY_SCHEMES: OpenAPI `securitySchemes` JSON with list of auth configs
    :ivar SECURITY: OpenAPI `security` JSON at the global level
    :ivar PAGE_TEMPLATES: A dictionary of documentation page templates. The key is the
        name of the template, that is also used in the URL path, while the value is used
        to render the documentation page content. (Each page template should contain a
        `{spec_url}` placeholder, that'll be replaced by the actual OpenAPI spec URL in
        the rendered documentation page.
    """

    def __init__(self, **kwargs):
        self.PATH = "apidoc"
        self.FILENAME = "openapi.json"
        self.OPENAPI_VERSION = "3.0.3"
        self.MODE = "normal"
        self._SUPPORT_MODE = {"normal", "strict", "greedy"}
        self.ANNOTATIONS = False

        self.TITLE = "Service API Document"
        self.DESCRIPTION = None
        self.VERSION = "0.1"
        self.DOMAIN = None
        self.SERVERS: Optional[List[Server]] = []

        self.SECURITY_SCHEMES: Optional[List[SecurityScheme]] = None
        self.SECURITY = {}

        self.PAGE_TEMPLATES = DEFAULT_PAGE_TEMPLATES

        self.logger = logging.getLogger(__name__)

        self.update(**kwargs)

    @property
    def spec_url(self):
        return f"/{self.PATH}/{self.FILENAME}"

    def __repr__(self):
        display = "\n{:=^80}\n".format(self.__class__.__name__)
        for k, v in vars(self).items():
            if not k.startswith("__"):
                display += "| {:<30} {}\n".format(k, v)

        return display + "=" * 80

    def update(self, **kwargs):
        """
        update config from key-value pairs

        :param kwargs: key(case insensitive)-value pairs for config

        If the key is not in attributes, it will be ignored. Otherwise, the
        corresponding attribute will be updated. (Logging Level: INFO)
        """
        for key, value in kwargs.items():
            key = key.upper()
            if not hasattr(self, key):
                self.logger.info("[✗] Ignore unknown attribute '%s'", key)
            else:
                setattr(self, key, value)
                self.logger.info(
                    "[✓] Attribute '%s' has been updated to '%s'", key, value
                )

        assert self.MODE in self._SUPPORT_MODE, "unsupported MODE"
