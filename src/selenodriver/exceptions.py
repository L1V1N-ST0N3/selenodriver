class SelenoDriverException(Exception):
    """Base exception for selenodriver errors."""


WebDriverException = SelenoDriverException


class NoAlertPresentException(SelenoDriverException):
    """Raised when an operation requires an alert but none is open."""


class StaleElementReferenceException(SelenoDriverException):
    """Raised when an element is no longer attached to the document."""


class ElementClickInterceptedException(SelenoDriverException):
    """Raised when another element intercepts a click."""


class NoSuchElementException(SelenoDriverException):
    """Raised when an element lookup returns no matching element."""


class NoSuchWindowException(SelenoDriverException):
    """Raised when a window or tab handle cannot be found."""


class NoSuchFrameException(SelenoDriverException):
    """Raised when a frame cannot be found."""


class TimeoutException(SelenoDriverException):
    """Raised when a wait condition is not met before timeout."""
