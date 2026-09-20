from dataclasses import dataclass


class RetryableError(Exception):
    """Marker exception for failures that may be retried."""


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

    def should_retry(self, error: Exception, attempt: int) -> bool:
        return isinstance(error, RetryableError) and attempt < self.max_attempts
