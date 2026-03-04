"""
Custom exceptions so we can tell apart "the AI module blew up"
from "Postgres is down" when the orchestrator decides what to do.
"""


class ContextExtractionError(Exception):
    """Raised when the context extraction LLM call fails."""
    pass


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""
    pass


class ResponseGenerationError(Exception):
    """Raised when the response synthesis LLM call fails."""
    pass
