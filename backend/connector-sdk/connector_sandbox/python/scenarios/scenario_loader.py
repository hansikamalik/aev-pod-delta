from pathlib import Path

import yaml


SCENARIO_FILE = Path(__file__).with_name("scenarios.yaml")


def load_scenarios() -> dict:
    with SCENARIO_FILE.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    return data.get("scenarios", {})