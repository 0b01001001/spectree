PAGES = {
    # https://github.com/Redocly/redoc
    'redoc': """
<!DOCTYPE html>
<html>

<head>
    <title>ReDoc</title>
    <!-- needed for adaptive design -->
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?
    family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">

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
    <redoc spec-url='{}'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"> </script>
</body>

</html>""",
    # https://swagger.io
    'swagger': """
<!-- HTML for static distribution bundle build -->
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Swagger UI</title>
        <link rel="stylesheet" type="text/css"
        href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.css" >
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

        <script
src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-bundle.js"></script>
        <script
src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-standalone-preset.js"></script>
        <script>
        window.onload = function() {{
        // Begin Swagger UI call region
        const ui = SwaggerUIBundle({{
            url: "{}",
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
            SwaggerUIBundle.presets.apis,
            SwaggerUIStandalonePreset
            ],
            plugins: [
            SwaggerUIBundle.plugins.DownloadUrl
            ],
            layout: "StandaloneLayout"
        }})
        // End Swagger UI call region

        window.ui = ui
        }}
    </script>
    </body>
</html>""",
}
