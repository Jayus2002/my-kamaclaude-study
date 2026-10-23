from datetime import datetime
import argparse
from importlib.metadata import version

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", help="The message to print")
    parser.add_argument("--version", action="version", version=f"%(prog)s {version('my-kamaclaude')}")
    args = parser.parse_args()
    if args.message:
        print(args.message)
    else:
        print(datetime.now())
