class Config:
    """
    :ivar MODE: mode for route. **normal** includes undecorated routes and
        routes decorated by this instance. **strict** only includes routes
        decorated by this instance. **greedy** includes all the routes.
    :ivar PATH: path for API document page
    :ivar UI: UI for API document, 'redoc' or 'swagger'
    :ivar OPENAPI_VERSION: OpenAPI version
    :ivar TITLE: service name
    :ivar VERSION: service version
    :ivar DOMAIN: service host domain
    """

    def __init__(self, **kwargs):
        self.PATH = 'apidoc'
        self.FILENAME = 'openapi.json'
        self.OPENAPI_VERSION = '3.0.2'
        self.UI = 'redoc'
        self._SUPPORT_UI = {'redoc', 'swagger'}
        self.MODE = 'normal'
        self._SUPPORT_MODE = {'normal', 'strict', 'greedy'}

        self.TITLE = 'Service API Document'
        self.VERSION = '0.1'
        self.DOMAIN = None

        self.update(**kwargs)

    @property
    def spec_url(self):
        return f'/{self.PATH}/{self.FILENAME}'

    def __repr__(self):
        display = '\n{:=^80}\n'.format(self.__class__.__name__)
        for k, v in vars(self).items():
            if not k.startswith('__'):
                display += '| {:<30} {}\n'.format(k, v)

        return display + '=' * 80

    def update(self, **kwargs):
        """
        update config from key-value pairs

        :param kwargs: key(case insensitive)-value pairs for config
        """
        for key, value in kwargs.items():
            key = key.upper()
            if not hasattr(self, key):
                print(f'[✗] Ignore unknown attribute "{key}"')
            else:
                setattr(self, key, value)
                print(f'[✓] Attribute "{key}" has been updated to "{value}"')

        assert self.UI in self._SUPPORT_UI, 'unsupported UI'
        assert self.MODE in self._SUPPORT_MODE, 'unsupported MODE'
