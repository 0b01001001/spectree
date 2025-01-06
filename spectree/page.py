from typing import Dict

ONLINE_PAGE_TEMPLATES: Dict[str, str] = {
    # https://github.com/Redocly/redoc
    "redoc": """
<!DOCTYPE html>
<html>
    <head>
        <title>ReDoc</title>
        <!-- needed for adaptive design -->
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%221em%22 font-size=%2280%22>📄</text></svg>">
        <link href=
        "https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700"
        rel="stylesheet">

        <!--
        ReDoc doesn't change outer page styles
        -->
        <style>
        body {{
            margin: 0;
            padding: 0;
        }}
        </style>
    </head>
    <body>
        <redoc spec-url='{spec_url}'></redoc>
        <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"> </script>
    </body>
</html>""",
    # https://swagger.io
    "swagger": """
<!-- HTML for static distribution bundle build -->
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="description" content="SwaggerUI"/>
        <title>SwaggerUI</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css" />
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%221em%22 font-size=%2280%22>📄</text></svg>">
    </head>

    <body>
        <div id="swagger-ui"></div>

        <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js" crossorigin></script>
        <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-standalone-preset.js" crossorigin></script>
        <script>
        window.onload = function() {{
        var full = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '');
        // Begin Swagger UI call region
        const ui = SwaggerUIBundle({{
            url: "{spec_url}",
            dom_id: '#swagger-ui',
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIStandalonePreset
            ],
            layout: "StandaloneLayout",
            oauth2RedirectUrl: full + "/{spec_path}/swagger/oauth2-redirect.html",
        }});
        ui.initOAuth({{
            clientId: "{client_id}",
            clientSecret: "{client_secret}",
            realm: "{realm}",
            appName: "{app_name}",
            scopeSeparator: "{scope_separator}",
            additionalQueryStringParams: {additional_query_string_params},
            useBasicAuthenticationWithAccessCodeGrant: {use_basic_authentication_with_access_code_grant},
            usePkceWithAuthorizationCodeGrant: {use_pkce_with_authorization_code_grant},
        }});
        // End Swagger UI call region

        window.ui = ui;
        }}
    </script>
    </body>
</html>""",
    "swagger/oauth2-redirect.html": """
<!DOCTYPE html>
<html lang="en-US">
<head>
    <title>Swagger UI: OAuth2 Redirect</title>
</head>
<body>
<script>
    'use strict';
    function run () {{
        var oauth2 = window.opener.swaggerUIRedirectOauth2;
        var sentState = oauth2.state;
        var redirectUrl = oauth2.redirectUrl;
        var isValid, qp, arr;

        if (/code|token|error/.test(window.location.hash)) {{
            qp = window.location.hash.substring(1);
        }} else {{
            qp = location.search.substring(1);
        }}

        arr = qp.split("&");
        arr.forEach(function (v,i,_arr) {{ _arr[i] = '"' + v.replace('=', '":"') + '"';}});
        qp = qp ? JSON.parse('{{' + arr.join() + '}}',
                function (key, value) {{
                    return key === "" ? value : decodeURIComponent(value);
                }}
        ) : {{}};

        isValid = qp.state === sentState;

        if ((
          oauth2.auth.schema.get("flow") === "accessCode" ||
          oauth2.auth.schema.get("flow") === "authorizationCode" ||
          oauth2.auth.schema.get("flow") === "authorization_code"
        ) && !oauth2.auth.code) {{
            if (!isValid) {{
                oauth2.errCb({{
                    authId: oauth2.auth.name,
                    source: "auth",
                    level: "warning",
                    message: "Authorization may be unsafe, passed state was changed in server Passed state wasn't returned from auth server"
                }});
            }}

            if (qp.code) {{
                delete oauth2.state;
                oauth2.auth.code = qp.code;
                oauth2.callback({{auth: oauth2.auth, redirectUrl: redirectUrl}});
            }} else {{
                let oauthErrorMsg;
                if (qp.error) {{
                    oauthErrorMsg = "["+qp.error+"]: " +
                        (qp.error_description ? qp.error_description+ ". " : "no accessCode received from the server. ") +
                        (qp.error_uri ? "More info: "+qp.error_uri : "");
                }}

                oauth2.errCb({{
                    authId: oauth2.auth.name,
                    source: "auth",
                    level: "error",
                    message: oauthErrorMsg || "[Authorization failed]: no accessCode received from the server"
                }});
            }}
        }} else {{
            oauth2.callback({{auth: oauth2.auth, token: qp, isValid: isValid, redirectUrl: redirectUrl}});
        }}
        window.close();
    }}

    window.addEventListener('DOMContentLoaded', function () {{
      run();
    }});
</script>
</body>
</html>""",
    "scalar": """
<!doctype html>
<html>
  <head>
    <title>API Reference</title>
    <meta charset="utf-8" />
    <meta
      name="viewport"
      content="width=device-width, initial-scale=1" />
    <style>
      body {{
        margin: 0;
      }}
    </style>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%221em%22 font-size=%2280%22>📄</text></svg>">
  </head>
  <body>
    <script
      id="api-reference"
      data-url="{spec_url}">
    </script>
    <script>
      var configuration = {{
        theme: 'purple',
      }}

      var apiReference = document.getElementById('api-reference')
      apiReference.dataset.configuration = JSON.stringify(configuration)
    </script>
    <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
  </body>
</html>""",
}

try:
    from offapi import OpenAPITemplate

    PAGE_TEMPLATES = {
        "redoc": OpenAPITemplate.REDOC.value,
        "swagger": OpenAPITemplate.SWAGGER.value,
        "scalar": OpenAPITemplate.SCALAR.value,
    }
except ImportError:
    PAGE_TEMPLATES = ONLINE_PAGE_TEMPLATES
