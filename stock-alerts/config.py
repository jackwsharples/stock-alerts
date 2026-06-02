import os
from dotenv import load_dotenv

REQUIRED_VARS = [
    "NTFY_TOPIC",
]


def load_config() -> dict:
    """Loads .env, validates all required vars are present, returns a config dict."""
    load_dotenv()
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in your Twilio credentials."
        )
    return {v: os.environ[v] for v in REQUIRED_VARS}
