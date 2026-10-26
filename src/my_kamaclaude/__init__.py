from datetime import datetime
import argparse
from importlib.metadata import version
import logging
from pathlib import Path
from .config import Config, load_config
from .logging_setup import setup_logging

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", help="The message to print")
    parser.add_argument("--version", action="version", version=f"%(prog)s {version('my-kamaclaude')}")
    parser.add_argument("--config", 
                        type=Path,
                        help="Path to the configuration file")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        setup_logging(config.data_dir)
    except (OSError, ValueError, TypeError) as e:
        parser.error(f"Error loading configuration: {e}")

    logger = logging.getLogger(__name__)
    logger.info("Starting my-kamaclaude application")
    try:
        print(f"Configuration loaded: {config}")
        if args.message:
            print(args.message)
        else:
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    finally:
        logger.info("Exiting my-kamaclaude application")