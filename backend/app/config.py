"""
Configuration management for the Ethera application.
Handles environment variables and app settings.
"""
import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/ethera")
    read_database_url: str = os.getenv("READ_DATABASE_URL", "")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # Kafka
    kafka_brokers: str = os.getenv("KAFKA_BROKERS", "kafka:9092")
    kafka_enabled: bool = os.getenv("KAFKA_ENABLED", "false").lower() == "true"
    
    # JWT
    jwt_secret: str = os.getenv("JWT_SECRET", "development-only-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))
    bootstrap_admin_username: str = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin")
    bootstrap_admin_password: str = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "change-me")
    
    # API
    api_title: str = "Ethera Inventory Management API"
    api_version: str = "2.0.0"
    api_description: str = "Production-grade inventory & order management system"
    
    # Rate limiting
    rate_limit_enabled: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    requests_per_minute: int = int(os.getenv("REQUESTS_PER_MINUTE", "60"))
    global_requests_per_minute: int = int(os.getenv("GLOBAL_REQUESTS_PER_MINUTE", "1000"))
    
    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100
    
    # Feature flags
    enable_kafka: bool = kafka_enabled
    enable_redis_cache: bool = os.getenv("ENABLE_CACHE", "true").lower() == "true"
    enable_auth: bool = os.getenv("ENABLE_AUTH", "true").lower() == "true"
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")

    # Observability
    service_name: str = os.getenv("OTEL_SERVICE_NAME", "ethera-api")
    otlp_endpoint: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    sentry_dsn: str = os.getenv("SENTRY_DSN", "")
    sentry_environment: str = os.getenv("SENTRY_ENVIRONMENT", "development")
    sentry_traces_sample_rate: float = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    json_logs: bool = os.getenv("JSON_LOGS", "true").lower() == "true"
    
    class Config:
        env_file = ".env"

    @property
    def allowed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

settings = Settings()
