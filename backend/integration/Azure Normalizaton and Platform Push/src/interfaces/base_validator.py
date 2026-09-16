import abc
from typing import Dict, Any, Tuple, List


class BaseValidator(abc.ABC):
    """Abstract Base Contract for schema and attribute validation engines."""

    @abc.abstractmethod
    def validate(self, asset_payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates a normalized asset dictionary against contract schema constraints.
        
        :param asset_payload: Transformed CAM asset dictionary.
        :return: Tuple containing (is_valid: bool, list_of_error_strings: List[str]).
        """
        pass
