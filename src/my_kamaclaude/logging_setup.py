import logging
from pathlib import Path

def setup_logging(data_dir: Path) -> None:
    logging.basicConfig(
        filename = data_dir / "app.log",
        encoding = "utf-8",
        level = logging.INFO,
        format = "%(asctime)s - %(levelname)s - %(message)s",
    )