from typing import List, Literal
from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: SecretStr
    log_level: str = "INFO"

    scrapper_base_url: str = "http://127.0.0.1:8000"

    notification_transport: Literal["kafka", "http"] = "kafka"

    kafka_bootstrap_servers: str = "localhost:9092,localhost:9093,localhost:9094"
    kafka_topic_notifications: str = "link-updates"
    kafka_consumer_group_id: str = "bot-service-group"
    kafka_auto_offset_reset: str = "latest"
    kafka_enable_auto_commit: bool = False

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

    rate_limit_requests_per_minute: int = Field(ge=1, default=200)
    rate_limit_enabled: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_commands: List[dict] = [
        {"command": "start", "description": "Запускает бота."},
        {"command": "help", "description": "Показывает справку по командам."},
        {"command": "track", "description": "Добавить ссылку для отслеживания."},
        {"command": "list", "description": "Показать отслеживаемые ссылки."},
        {"command": "untrack", "description": "Перестать отслеживать ссылку."},
        {"command": "cancel", "description": "Отменить текущий диалог."},
    ]

    @property
    def retry_statuses(self) -> list[int]:
        return [int(x.strip()) for x in self.retry_statuses_str.split(",") if x.strip()]


settings = Settings()
