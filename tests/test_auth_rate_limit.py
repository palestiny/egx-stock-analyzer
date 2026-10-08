from app.api.auth_rate_limit import AuthenticationRateLimiter


def test_rate_limiter_bounds_tracked_client_memory():
    limiter = AuthenticationRateLimiter(
        max_failures=2,
        window_seconds=60,
        max_tracked_clients=2,
    )
    limiter.record_failure("client-a")
    limiter.record_failure("client-b")
    limiter.record_failure("client-c")

    assert len(limiter._failures) == 2
    assert limiter.is_blocked("client-b")
    assert not limiter.is_blocked("client-a")
