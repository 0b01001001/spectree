import pytest

# Enable pytest assertion rewriting for dry module. Must come before module is imported.
pytest.register_assert_rewrite("tests.flask_imports.dry_plugin_flask")

from .dry_plugin_flask import (  # noqa: E402
    test_flask_doc,
    test_flask_list_json_request,
    test_flask_make_response_get,
    test_flask_make_response_post,
    test_flask_no_response,
    test_flask_optional_alias_response,
    test_flask_return_list_request,
    test_flask_return_model,
    test_flask_skip_validation,
    test_flask_upload_file,
    test_flask_validate_post_data,
    test_flask_validation_error_response_status_code,
)

__all__ = [
    "test_flask_return_model",
    "test_flask_skip_validation",
    "test_flask_validation_error_response_status_code",
    "test_flask_doc",
    "test_flask_optional_alias_response",
    "test_flask_validate_post_data",
    "test_flask_no_response",
    "test_flask_upload_file",
    "test_flask_list_json_request",
    "test_flask_return_list_request",
    "test_flask_make_response_post",
    "test_flask_make_response_get",
]
