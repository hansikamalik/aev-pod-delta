import abc
from typing import Dict, Any, List


class BasePushEngine(abc.ABC):
    """Abstract Base Contract for platform ingestion batch shipping and error handling."""

    @abc.abstractmethod
    def push_batch(self, assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Pushes a list of normalized and validated assets to the upstream target endpoint.
        
        :param assets: List of valid CAM asset dictionaries.
        :return: Execution summary dict containing total, successful, failed, and dlq_count.
        """
        pass

    @abc.abstractmethod
    def route_to_dlq(self, failed_assets: List[Dict[str, Any]], reason: str) -> None:
        """
        Routes failed or unprocessable assets to Dead Letter Queue storage/file.
        
        :param failed_assets: List of rejected asset dictionaries.
        :param reason: Error category or message explaining the failure.
        """
        pass
