"""
Domain exceptions raised by the services and translated to HTTP by the routers.

Services know nothing about HTTP; a router catches these and picks the status
code, so the same service can back a CLI or a job without changes.
"""


class AppError(Exception):
    """Base class for every domain error."""


class IdentifierTakenError(AppError):
    """A username, email or phone number is already used by another account."""


class PasswordVerificationError(AppError):
    """The password offered to confirm an action does not match the account's."""
