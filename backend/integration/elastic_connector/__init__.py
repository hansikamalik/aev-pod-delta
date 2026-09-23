"""
Elasticsearch Connector implementation conforming to Connector SDK Contract v2.
"""

from elastic_connector.connector import ElasticConnector
from elastic_connector.client import ElasticClient
from elastic_connector.config import ElasticConfig, ElasticCredentials
from elastic_connector.models import Asset, AssetType, SyncResult

__all__ = [
    "ElasticConnector",
    "ElasticClient",
    "ElasticConfig",
    "ElasticCredentials",
    "Asset",
    "AssetType",
    "SyncResult",
]
