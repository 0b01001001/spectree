"""
Helper functions for validation operations.

Extracted from SpecTree to improve separation of concerns.
"""

from typing import Optional
import warnings


def check_validation_compatibility(
    annotations_enabled: bool,
    skip_validation: bool
) -> None:
    """Check if validation settings are compatible.
    
    Warns if annotations are enabled but validation is skipped,
    as this combination results in None values.
    
    Args:
        annotations_enabled: Whether annotation mode is enabled
        skip_validation: Whether validation is skipped
    """
    if annotations_enabled and skip_validation:
        warnings.warn(
            "`skip_validation` cannot be used with `annotations` enabled. The instances"
            " of `json`, `headers`, `cookies`, etc. read from function will be `None`.",
            UserWarning,
            stacklevel=3,  # Adjusted for call depth
        )


def get_effective_validation_status(
    endpoint_status: int,
    global_status: int
) -> int:
    """Get the effective validation error status code.
    
    Uses endpoint-specific status if provided, otherwise falls back to global.
    
    Args:
        endpoint_status: Status code specific to endpoint (0 if not set)
        global_status: Global default status code
    
    Returns:
        The status code to use for validation errors
    """
    if endpoint_status == 0:
        return global_status
    return endpoint_status