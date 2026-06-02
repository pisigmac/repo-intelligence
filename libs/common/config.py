"""Application configuration using Pydantic Settings."""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "repo-intelligence"
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://repo:repo@localhost/repo_intelligence",
        alias="DATABASE_URL"
    )

    # Kafka
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        alias="KAFKA_BOOTSTRAP_SERVERS"
    )
    kafka_group_id: str = Field(default="repo-intel", alias="KAFKA_GROUP_ID")

    # Storage
    repo_storage_path: str = Field(default="/tmp/repos", alias="REPO_STORAGE_PATH")

    # Vector DB
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")

    # Service discovery
    ingestion_service_url: str = "http://ingestion-service:8080"
    parser_service_url: str = "http://parser-service:8080"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
