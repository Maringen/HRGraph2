import os
import sys
from dotenv import load_dotenv

load_dotenv()


def validate_required_env_vars():
    """Validate required environment variables are present."""
    required_vars = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(
            f"Error: Missing required environment variables: {', '.join(missing_vars)}"
        )
        print("Please set these in your .env file or environment")
        sys.exit(1)


validate_required_env_vars()

FALKORDB_HOST = os.getenv("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.getenv("FALKORDB_PORT", 6379))
FALKORDB_DB = os.getenv("FALKORDB_DB", "hr_temporal")

GRAPHITI_DB_URL = os.getenv("GRAPHITI_DB_URL")
if not GRAPHITI_DB_URL:
    if FALKORDB_HOST != "localhost":
        GRAPHITI_DB_URL = f"bolt://{FALKORDB_HOST}:7687"
    else:
        GRAPHITI_DB_URL = "sqlite:///graphiti.db"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


def get_config():
    """Return configuration dictionary for validation."""
    return {
        "falkordb_host": FALKORDB_HOST,
        "falkordb_port": FALKORDB_PORT,
        "falkordb_db": FALKORDB_DB,
        "graphiti_db_url": GRAPHITI_DB_URL,
        "has_openai_key": bool(OPENAI_API_KEY),
        "has_anthropic_key": bool(ANTHROPIC_API_KEY),
    }
