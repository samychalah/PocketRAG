"""Idiomatic exception translation for the NotebookLM API surface.

This module maps HTTP status codes from the Google Discovery Engine v1 REST API
to idiomatic Python exceptions. It provides a clean boundary for handling
common API errors, such as authorization failures, resource absence, or quota limits.
"""
from __future__ import annotations


class NotebookLMError(Exception):
    """Base exception for all NotebookLM-related operations.
    
    All custom errors defined in this project inherit from this class,
    allowing callers to catch all NotebookLM errors in a single except block.
    """


class NotebookNotFoundError(NotebookLMError):
    """Raised when a requested notebook ID is not found or does not exist."""
    pass


class PermissionDeniedError(NotebookLMError):
    """Raised when the credentials do not have permission to access the resource (403 Forbidden)."""
    pass


class QuotaExceededError(NotebookLMError):
    """Raised when the API rate limit or quota is exceeded (429 Too Many Requests).
    
    This error triggers the exponential backoff retry policy in the client.
    """
    pass


class ApiError(NotebookLMError):
    """Generic non-2xx response from the API that is not explicitly mapped.

    Attributes:
        status: The HTTP status code returned by the API.
        body: The raw response body content.
    """

    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"API error {status}: {body}")


def translate(status: int, body: str) -> NotebookLMError:
    """Map an HTTP status code to an idiomatic Python NotebookLMError exception.

    Args:
        status: The HTTP status code from the REST response.
        body: The response body text.

    Returns:
        An instance of a subclass of NotebookLMError corresponding to the status code,
        or an ApiError for unmapped status codes.
    """
    if status == 403:
        return PermissionDeniedError(body)
    if status == 404:
        return NotebookNotFoundError(body)
    if status == 429:
        return QuotaExceededError(body)
    return ApiError(status, body)
