class SelenoDriverException(Exception):
    """Base exception for selenodriver errors."""


class NoSuchElementException(SelenoDriverException):
    """Raised when an element lookup returns no matching element."""


class NoSuchWindowException(SelenoDriverException):
    """Raised when a window or tab handle cannot be found."""


class NoSuchFrameException(SelenoDriverException):
    """Raised when a frame cannot be found."""


class TimeoutException(SelenoDriverException):
    """Raised when a wait condition is not met before timeout."""
