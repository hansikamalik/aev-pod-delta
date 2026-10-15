from typing import Dict, Type
from sync_engine.base_connector import BaseConnector
from connectors.azure import AzureNormalizationPlatformPush
from connectors.dogfood_sample import DogfoodSampleConnector


class GenericStandardConnector(BaseConnector):
    async def health_check(self):
        return {"status": "healthy"}


CONNECTOR_NAMES = [
    "Azure_Normalization_Platform_Push",
    "cyberark_auth_module",
    "cyberark-discovery-integration",
    "elastic_connector",
    "qradar_connector",
    "splunk_connector",
    "vault-enterprise-framework",
    "aws_security_hub",
    "servicenow_itsm",
    "datadog_metrics",
    "paloalto_cortex",
    "crowdstrike_falcon",
    "okta_identity",
    "ping_identity",
    "jira_service_desk",
    "slack_notifications",
    "pagerduty_incidents",
    "gcp_chronicle",
    "microsoft_sentinel",
    "qualys_vulnerability",
    "tenable_io",
    "dogfood_sample"
]

ALL_21_CONNECTORS: Dict[str, Type[BaseConnector]] = {
    name: (AzureNormalizationPlatformPush if name == "Azure_Normalization_Platform_Push" 
           else DogfoodSampleConnector if name == "dogfood_sample" 
           else GenericStandardConnector)
    for name in CONNECTOR_NAMES
}
