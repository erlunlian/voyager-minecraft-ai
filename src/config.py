"""Configuration management for Voyager AI."""

import os

from dotenv import load_dotenv


class Config:
    """Configuration loader and validator."""

    def __init__(self):
        """Initialize and load configuration from environment."""
        load_dotenv()

        # Azure OpenAI
        self.azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

        # Validate Azure credentials
        if not self.azure_api_key or not self.azure_endpoint:
            raise ValueError("Azure OpenAI credentials not found in .env file")

        # Database configuration
        self.db_config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "database": os.getenv("POSTGRES_DB", "voyager_db"),
            "user": os.getenv("POSTGRES_USER", "voyager"),
            "password": os.getenv("POSTGRES_PASSWORD", "voyager_pass"),
        }

        # Minecraft configuration
        self.minecraft_config = {
            "host": os.getenv("MINECRAFT_HOST", "localhost"),
            "port": int(os.getenv("MINECRAFT_PORT", "25565")),
            "username": os.getenv("MINECRAFT_USERNAME", "VoyagerBot"),
        }

        # ChromaDB configuration
        self.chroma_host = os.getenv("CHROMA_HOST", "localhost")
        self.chroma_port = int(os.getenv("CHROMA_PORT", "8000"))

    def get_db_url(self) -> str:
        """Get SQLAlchemy database URL."""
        return (
            f"postgresql+psycopg2://{self.db_config['user']}:{self.db_config['password']}"
            f"@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
        )

    def __repr__(self):
        return f"<Config(minecraft={self.minecraft_config['host']}, db={self.db_config['host']})>"
