from typing import Dict

DEFAULT_PAGE_TEMPLATES: Dict[str, str] = {
    # https://github.com/Redocly/redoc
    "redoc": """
<!DOCTYPE html>
<html>
    <head>
        <title>ReDoc</title>
        <!-- needed for adaptive design -->
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
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
</html>""",  # noqa: E501
    # https://swagger.io
    "swagger": """
<!-- HTML for static distribution bundle build -->
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Swagger UI</title>
        <link rel="stylesheet" type="text/css"
        href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css" >
        <style>
        html
        {{
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }}

        *,
        *:before,
        *:after
        {{
            box-sizing: inherit;
        }}

        body
        {{
            margin:0;
            background: #fafafa;
        }}
        </style>
    </head>

    <body>
        <div id="swagger-ui"></div>

        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-standalone-preset.js"></script>
        <script>
        window.onload = function() {{
        var full = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '');
        // Begin Swagger UI call region
        const ui = SwaggerUIBundle({{
            url: "{spec_url}",
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
            SwaggerUIBundle.presets.apis,
            SwaggerUIStandalonePreset
            ],
            plugins: [
            SwaggerUIBundle.plugins.DownloadUrl
            ],
            oauth2RedirectUrl: full + "/{spec_path}/swagger/oauth2-redirect.html",
            layout: "StandaloneLayout"
        }})
        ui.initOAuth({{
            clientId: "{client_id}",
            clientSecret: "{client_secret}",
            realm: "{realm}",
            appName: "{app_name}",
            scopeSeparator: "{scope_separator}",
            additionalQueryStringParams: {additional_query_string_params},
            useBasicAuthenticationWithAccessCodeGrant: {use_basic_authentication_with_access_code_grant},
            usePkceWithAuthorizationCodeGrant: {use_pkce_with_authorization_code_grant}
        }})
        // End Swagger UI call region

        window.ui = ui
        }}
    </script>
    </body>
</html>""",  # noqa: E501
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
</html>""",  # noqa: E501
}
