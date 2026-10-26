from typing import Dict, Type
from sync_engine.base_connector import BaseConnector

from integration.azure_normalization_platform_push import AzureNormalizationPlatformPush
from integration.ae_microsoft_entra_id_connector import MicrosoftEntraIDConnector
from integration.active_directory_connector import ActiveDirectoryConnector
from integration.aev_connector_webhook import AEVConnectorWebhook
from integration.azure_auth_module import AzureAuthModule
from integration.azure_discovery import AzureDiscoveryConnector
from integration.connector_github import ConnectorGitHub
from integration.connector_gitlab import ConnectorGitLab
from integration.connector_microsoft_sentinel import ConnectorMicrosoftSentinel
from integration.connector_sentinelone import ConnectorSentinelOne
from integration.cyberark_auth_module import CyberArkAuthModule
from integration.cyberark_discovery_integration import CyberArkDiscoveryIntegration
from integration.elastic_connector import ElasticConnector
from integration.google_workspace_auth import GoogleWorkspaceAuth
from integration.google_workspace_connector import GoogleWorkspaceConnector
from integration.jira_connector import JiraConnector
from integration.microsoft_defender_connector import MicrosoftDefenderConnector
from integration.microsoft365_connector import Microsoft365Connector
from integration.okta_connector import OktaConnector
from integration.qradar_connector import QRadarConnector
from integration.servicenow_connector import ServiceNowConnector
from integration.splunk_connector import SplunkConnector
from integration.vault_enterprise_framework import VaultEnterpriseFramework

ALL_CONNECTORS: Dict[str, Type[BaseConnector]] = {
    "Azure_Normalization_Platform_Push": AzureNormalizationPlatformPush,
    "AEV-microsoft-entra-id-connector": MicrosoftEntraIDConnector,
    "active-directory-connector": ActiveDirectoryConnector,
    "aev-connector-webhook": AEVConnectorWebhook,
    "azure-auth-module": AzureAuthModule,
    "azure_discovery": AzureDiscoveryConnector,
    "connector-github": ConnectorGitHub,
    "connector-gitlab": ConnectorGitLab,
    "connector-microsoft-sentinel": ConnectorMicrosoftSentinel,
    "connector-sentinelone": ConnectorSentinelOne,
    "cyberark_auth_module": CyberArkAuthModule,
    "cyberark-discovery-integration": CyberArkDiscoveryIntegration,
    "elastic_connector": ElasticConnector,
    "google-workspace-auth": GoogleWorkspaceAuth,
    "google-workspace-connector": GoogleWorkspaceConnector,
    "jira_connector": JiraConnector,
    "microsoft-defender-connector": MicrosoftDefenderConnector,
    "microsoft365-connector": Microsoft365Connector,
    "okta_connector": OktaConnector,
    "qradar_connector": QRadarConnector,
    "servicenow-connector": ServiceNowConnector,
    "splunk_connector": SplunkConnector,
    "vault-enterprise-framework": VaultEnterpriseFramework,
}
