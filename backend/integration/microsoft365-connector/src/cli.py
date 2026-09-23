"""
Minimal CLI entrypoint: load config, run one sync, print the result.
Wire this into the squad's actual scheduler/orchestration instead of running
it standalone, once that exists.
"""

import argparse
import json
import logging

from .config import load_config
from .connector import Microsoft365Connector


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Microsoft 365 connector once.")
    parser.add_argument("--config", required=True, help="Path to config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    logging.basicConfig(level=config.log_level)

    connector = Microsoft365Connector(config)
    result = connector.run_sync()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
