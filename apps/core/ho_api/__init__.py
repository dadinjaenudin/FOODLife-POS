"""
HO (Head Office) API Integration Module

This module handles all communication with the HO Server API.
"""

from .client import HOAPIClient
from .exceptions import (
    HOAPIException,
    HOAPIConnectionError,
    HOAPIAuthenticationError,
    HOAPINotFoundError,
    HOAPIValidationError
)

__all__ = [
    'HOAPIClient',
    'HOAPIException',
    'HOAPIConnectionError',
    'HOAPIAuthenticationError',
    'HOAPINotFoundError',
    'HOAPIValidationError',
]
