from collections import deque
from threading import Lock
from time import monotonic


class AuthenticationRateLimiter:
    """Process-local sliding-window limiter for repeated failed authentication."""

    def __init__(
        self,
        max_failures: int = 10,
        window_seconds: int = 60,
        max_tracked_clients: int = 10_000,
    ) -> None:
        if max_failures < 1 or window_seconds < 1 or max_tracked_clients < 1:
            raise ValueError("rate-limit values must be positive")
        self._max_failures = max_failures
        self._window_seconds = window_seconds
        self._max_tracked_clients = max_tracked_clients
        self._failures: dict[str, deque[float]] = {}
        self._lock = Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        attempts = self._failures.get(key)
        if attempts is None:
            if len(self._failures) >= self._max_tracked_clients:
                self._failures.pop(next(iter(self._failures)))
            attempts = deque()
            self._failures[key] = attempts
        cutoff = now - self._window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        return attempts

    def is_blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._prune(key, monotonic())) >= self._max_failures

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = monotonic()
            attempts = self._prune(key, now)
            attempts.append(now)

    def record_success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def retry_after_seconds(self, key: str) -> int:
        with self._lock:
            attempts = self._prune(key, monotonic())
            if len(attempts) < self._max_failures:
                return 0
            return max(1, int(self._window_seconds - (monotonic() - attempts[0]) + 0.999))
