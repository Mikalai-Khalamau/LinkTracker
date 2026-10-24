from slowapi import Limiter
from slowapi.util import get_remote_address
from src.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_requests_per_minute}/minute"],
    enabled=settings.rate_limit_enabled,
)
