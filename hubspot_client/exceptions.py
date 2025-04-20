# hubspot_client/exceptions.py

class HubSpotError(Exception):
    """Base exception for HubSpot client errors."""
    def __init__(self, message="An error occurred with the HubSpot API", status_code=None, original_exception=None):
        self.status_code = status_code
        self.original_exception = original_exception
        # Attempt to get more details from original exception if available
        details = ""
        if original_exception:
            if hasattr(original_exception, 'response') and original_exception.response is not None:
                try:
                    details = f" - Response: {original_exception.response.text}"
                except Exception:
                    details = " - Response body unavailable"
            elif hasattr(original_exception, 'body') and original_exception.body is not None:
                details = f" - Body: {original_exception.body}"

        full_message = f"{message}{details}"
        super().__init__(full_message)

class HubSpotAuthenticationError(HubSpotError):
    """Raised for authentication issues (e.g., invalid API key)."""
    def __init__(self, message="HubSpot authentication failed (401)", status_code=401, original_exception=None):
        super().__init__(message, status_code, original_exception)

class HubSpotRateLimitError(HubSpotError):
    """Raised when HubSpot API rate limits are exceeded."""
    def __init__(self, message="HubSpot API rate limit exceeded (429)", status_code=429, original_exception=None):
        super().__init__(message, status_code, original_exception)

class HubSpotNotFoundError(HubSpotError):
    """Raised when a requested resource (e.g., contact) is not found."""
    def __init__(self, message="HubSpot resource not found (404)", status_code=404, original_exception=None):
        super().__init__(message, status_code, original_exception)

class HubSpotBadRequestError(HubSpotError):
    """Raised for invalid requests (e.g., malformed data)."""
    def __init__(self, message="HubSpot bad request (400)", status_code=400, original_exception=None):
        super().__init__(message, status_code, original_exception)

class HubSpotConflictError(HubSpotError):
    """Raised for conflicts (e.g., resource already exists)."""
    def __init__(self, message="HubSpot conflict (409)", status_code=409, original_exception=None):
        super().__init__(message, status_code, original_exception)

class HubSpotServerError(HubSpotError):
    """Raised for server-side errors on HubSpot's end."""
    def __init__(self, message="HubSpot server error (5xx)", status_code=500, original_exception=None):
        # Use actual status code if available
        if original_exception and hasattr(original_exception, 'response') and original_exception.response is not None:
            status_code = original_exception.response.status_code
        elif original_exception and hasattr(original_exception, 'status') and original_exception.status is not None:
            status_code = original_exception.status

        super().__init__(message, status_code, original_exception)

# You can add more specific errors if needed
