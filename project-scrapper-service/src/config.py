from typing import Literal
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000

    check_interval: int = Field(ge=60, default=300)
    batch_size: int = Field(ge=50, le=500, default=100)
    max_check_age_minutes: int = Field(ge=5, default=60)

    github_token: SecretStr | None = None
    stackoverflow_token: SecretStr | None = None

    bot_callback_url: str = "http://localhost:8080/updates"

    notification_transport: Literal["kafka", "http"] = "kafka"

    kafka_bootstrap_servers: str = "localhost:9092,localhost:9093,localhost:9094"
    kafka_topic_notifications: str = "link-updates"
    kafka_producer_client_id: str = "scrapper-service"
    kafka_ack_mode: str = "all"
    kafka_retries: int = 3
    kafka_linger_ms: int = 10
    kafka_batch_size: int = 16384

    valkey_enabled: bool = True
    valkey_cluster_nodes: str = "valkey-1:6379,valkey-2:6379,valkey-3:6379"
    valkey_cache_ttl: int = Field(ge=10, default=300)
    valkey_cache_prefix: str = "list:"

    log_level: str = "INFO"

    db_url: str = "postgresql://postgres:postgres@localhost:5432/linktracker"
    db_access_type: Literal["SQL", "ORM"] = "ORM"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    http_timeout_seconds: int = Field(ge=1, default=10)
    http_timeout_connect: int = Field(ge=1, default=5)

    retry_max_attempts: int = Field(ge=1, default=3)
    retry_wait_seconds: float = Field(ge=0.1, default=1.0)

    retry_statuses_str: str = Field(default="500,502,503,504", alias="retry_statuses")

    circuit_breaker_failure_rate_threshold: int = Field(ge=1, le=100, default=50)
    circuit_breaker_wait_duration_seconds: int = Field(ge=1, default=30)
    circuit_breaker_permitted_calls_half_open: int = Field(ge=1, default=3)
    circuit_breaker_sliding_window_size: int = Field(ge=1, default=10)
    circuit_breaker_minimum_required_calls: int = Field(ge=1, default=5)

    rate_limit_requests_per_minute: int = Field(ge=1, default=100)
    rate_limit_enabled: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def retry_statuses(self) -> list[int]:
        return [int(x.strip()) for x in self.retry_statuses_str.split(",") if x.strip()]


settings = Settings()
