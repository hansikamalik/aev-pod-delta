"""python -m connectors.servicenow.health_check --config config/servicenow.yaml"""

import argparse
import json
import sys

from .connector import ServiceNowConnector


def main() -> int:
    parser = argparse.ArgumentParser(description="ServiceNow connector health check")
    parser.add_argument("--config", default="config/servicenow.yaml")
    args = parser.parse_args()

    result = ServiceNowConnector(config_path=args.config).health_check()
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("overall_ok") else 1


if __name__ == "__main__":
    sys.exit(main())
