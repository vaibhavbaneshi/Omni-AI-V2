import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(log_level: str = "INFO") -> None:
    """Configure application logging to file and console with rotation."""
    logs_dir = Path("./logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "backend.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s [%(module)s:%(lineno)d] - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear existing handlers to avoid duplicate logs in dev reload
    if logger.handlers:
        logger.handlers = []

    # Railway captures stdout/stderr only — skip file logging in production.
    env = os.environ.get("ENVIRONMENT", "development").strip().lower()
    if env != "production":
        logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Reduce verbosity of some noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    # Ingestion pipeline — always show stage transitions in console during uploads.
    ingestion_logger = logging.getLogger("omniai.ingestion")
    ingestion_logger.setLevel(logging.DEBUG)
    ingestion_logger.propagate = True

    upload_logger = logging.getLogger("app.api.upload_routes")
    upload_logger.setLevel(logging.DEBUG)
