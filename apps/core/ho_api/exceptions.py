"""
Custom exceptions for HO API integration
"""


class HOAPIException(Exception):
    """Base exception for HO API errors"""
    pass


class HOAPIConnectionError(HOAPIException):
    """Raised when connection to HO Server fails"""
    pass


class HOAPIAuthenticationError(HOAPIException):
    """Raised when authentication with HO Server fails"""
    pass


class HOAPINotFoundError(HOAPIException):
    """Raised when requested resource is not found"""
    pass


class HOAPIValidationError(HOAPIException):
    """Raised when API request validation fails"""
    pass


class HOAPITimeoutError(HOAPIException):
    """Raised when API request times out"""
    pass
