from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings for the ingest pipeline."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mud_repo_path: Path = Field(..., alias="MUD_REPO_PATH")
    neo4j_uri: str = Field("bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field("neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(..., alias="NEO4J_PASSWORD")
    neo4j_database: str = Field("neo4j", alias="NEO4J_DATABASE")
    overlay_path: Path = Field(
        Path(__file__).parent.parent / "overlay.yml", alias="OVERLAY_PATH"
    )

    @field_validator("mud_repo_path")
    @classmethod
    def _abs_repo(cls, v: Path) -> Path:
        p = v.expanduser().resolve()
        if not p.is_dir():
            raise ValueError(f"MUD_REPO_PATH is not a directory: {p}")
        return p

    @property
    def backend_src(self) -> Path:
        return self.mud_repo_path / "mud-backend" / "src" / "main" / "java" / "com" / "mud"

    @property
    def migration_dir(self) -> Path:
        return (
            self.mud_repo_path
            / "mud-backend"
            / "src"
            / "main"
            / "resources"
            / "db"
            / "migration"
        )


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
