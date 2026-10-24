import json
import yaml
from src.discovery import LDAPScanner, CloudScanner, APIScanner
from src.normalization import Normalizer
from src.push import CyberArkClient, Onboarder
from src.utils.logger import get_logger

logger = get_logger("MainPipeline")

def load_configurations():
    with open("config/cyberark_config.yaml", "r") as f:
        cybr_config = yaml.safe_load(f)
    with open("config/discovery_targets.yaml", "r") as f:
        targets_config = yaml.safe_load(f)
    with open("config/normalization_rules.json", "r") as f:
        norm_rules = json.load(f)
    return cybr_config, targets_config, norm_rules

def run():
    logger.info("Initializing CyberArk Discovery and Onboarding Automation Framework")
    cybr_config, targets_config, norm_rules = load_configurations()

    # 1. Discovery Stage
    raw_accounts = []
    raw_accounts.extend(LDAPScanner(targets_config).scan())
    raw_accounts.extend(CloudScanner(targets_config).scan())
    raw_accounts.extend(APIScanner(targets_config).scan())
    logger.info(f"Total raw accounts gathered across all scanners: {len(raw_accounts)}")

    # 2. Normalization Stage
    normalizer = Normalizer(norm_rules)
    normalized_accounts = normalizer.process(raw_accounts)
    logger.info(f"Total accounts successfully normalized and validated: {len(normalized_accounts)}")

    # 3. Push Stage
    client = CyberArkClient(cybr_config)
    client.login(username="VaultAdmin", password="SamplePassword")
    
    onboarder = Onboarder(client)
    summary = onboarder.bulk_push(normalized_accounts)
    
    logger.info(f"Pipeline Completed successfully. Summary: {summary}")

if __name__ == "__main__":
    run()
