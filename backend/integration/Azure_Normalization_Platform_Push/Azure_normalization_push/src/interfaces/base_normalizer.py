import abc
from typing import Dict, Any, Optional


class BaseNormalizer(abc.ABC):
    """Abstract Base Contract for all resource-specific Azure normalizers."""

    def __init__(self, subscription_id: Optional[str] = None) -> None:
        self.subscription_id = subscription_id

    @abc.abstractmethod
    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforms raw ARM or Graph API JSON payload into standard CAM dictionary format.
        
        :param raw_data: Raw JSON dict loaded from Azure ARM or Graph API.
        :return: Transformed dictionary conforming to azure_cam_schema.json.
        """
        pass

    @abc.abstractmethod
    def extract_common_metadata(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts universal metadata fields (asset_id, name, region, tags, subscription_id).
        
        :param raw_data: Raw JSON payload.
        :return: Shared envelope attributes dictionary.
        """
        pass
