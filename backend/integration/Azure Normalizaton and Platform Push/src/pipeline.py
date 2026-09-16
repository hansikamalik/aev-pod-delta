from typing import List, Dict, Any
from src.normalizers.vm import VMNormalizer
from src.normalizers.storage import StorageNormalizer
from src.normalizers.aad import AADNormalizer
from src.normalizers.sql import SQLNormalizer
from src.normalizers.functions import FunctionAppNormalizer
from src.validator import AssetValidator
from src.push.platform_pusher import PlatformPushEngine


class AzureNormalizationPipeline:
    """Orchestrates ingestion, normalization, validation, and pushing for Azure resources."""

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        schema_path: str = None,
        dlq_dir: str = "dlq_output"
    ) -> None:
        self.validator = AssetValidator(schema_path=schema_path)
        self.pusher = PlatformPushEngine(
            endpoint_url=endpoint_url,
            api_key=api_key,
            dlq_dir=dlq_dir
        )
        self.normalizers = {
            "Microsoft.Compute/virtualMachines": VMNormalizer(),
            "Microsoft.Storage/storageAccounts": StorageNormalizer(),
            "Microsoft.Graph/users": AADNormalizer(),
            "Microsoft.Sql/servers/databases": SQLNormalizer(),
            "Microsoft.Web/sites": FunctionAppNormalizer()
        }

    def process_raw_payloads(self, raw_assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes end-to-end processing across raw input assets.
        """
        valid_normalized_assets = []
        invalid_assets = []

        for raw in raw_assets:
            # Determine native type
            native_type = raw.get("type")
            if not native_type and "userPrincipalName" in raw:
                native_type = "Microsoft.Graph/users"

            normalizer = self.normalizers.get(native_type)
            if not normalizer:
                invalid_assets.append({
                    "raw_payload": raw,
                    "reason": f"UNSUPPORTED_RESOURCE_TYPE: {native_type}"
                })
                continue

            # 1. Normalize
            normalized = normalizer.normalize(raw)

            # 2. Validate against schema contract
            is_valid, errors = self.validator.validate(normalized)
            if is_valid:
                valid_normalized_assets.append(normalized)
            else:
                invalid_assets.append({
                    "normalized_payload": normalized,
                    "reason": f"SCHEMA_VALIDATION_ERROR: {'; '.join(errors)}"
                })

        # Route validation failures directly to DLQ
        dlq_files = []
        if invalid_assets:
            dlq_file = self.pusher.route_to_dlq(invalid_assets, reason="VALIDATION_FAILED")
            dlq_files.append(dlq_file)

        # 3. Push valid normalized assets
        push_results = self.pusher.push_batch(valid_normalized_assets)
        push_results["dlq_files"].extend(dlq_files)
        push_results["validation_failed_count"] = len(invalid_assets)

        return push_results
