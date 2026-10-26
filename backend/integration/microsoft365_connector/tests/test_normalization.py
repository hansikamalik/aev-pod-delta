import unittest

from microsoft365_connector.exceptions import NormalizationError
from microsoft365_connector.models import AssetStatus, AssetType
from microsoft365_connector.normalization import normalize, normalize_findings

RAW = {
    "user": [
        {
            "id": "u-1",
            "displayName": "Asha Rao",
            "userPrincipalName": "asha.rao@contoso.com",
            "mail": "asha.rao@contoso.com",
            "accountEnabled": True,
            "jobTitle": "Analyst",
            "department": "Risk",
        }
    ],
    "group": [{"id": "g-1", "displayName": "Security Admins", "securityEnabled": True}],
    "device": [
        {
            "id": "d-1",
            "displayName": "ASHA-LAPTOP",
            "operatingSystem": "Windows",
            "accountEnabled": True,
            "registeredOwners": ["asha.rao@contoso.com"],
        }
    ],
    "domain": [{"id": "contoso.com", "isVerified": True, "isDefault": True}],
    "license": [
        {
            "skuId": "sku-1",
            "skuPartNumber": "ENTERPRISEPACK",
            "consumedUnits": 42,
            "capabilityStatus": "Enabled",
            "prepaidUnits": {"enabled": 50},
        }
    ],
}

RAW_AUDIT_LOG = {
    "audit_log": [
        {
            "id": "al-1",
            "category": "UserManagement",
            "result": "success",
            "resultReason": "",
            "activityDisplayName": "Add user",
            "activityDateTime": "2026-09-20T10:15:00Z",
            "loggedByService": "Core Directory",
            "operationType": "Add",
            "initiatedBy": {"user": {"userPrincipalName": "admin@contoso.com"}},
            "targetResources": [{"id": "u-2", "displayName": "Devon Lee", "type": "User"}],
        }
    ]
}


class TestNormalization(unittest.TestCase):
    def test_normalize_produces_one_asset_per_raw_object(self):
        assets = normalize(RAW)
        self.assertEqual(len(assets), 5)

    def test_normalize_skips_finding_type_resources(self):
        combined = dict(RAW, **RAW_AUDIT_LOG)
        assets = normalize(combined)
        # audit_log entries are Findings, not Assets — normalize() should
        # skip them rather than raising or counting them as assets.
        self.assertEqual(len(assets), 5)

    def test_normalize_user_fields(self):
        [asset] = normalize({"user": RAW["user"]})
        self.assertEqual(asset.asset_type, AssetType.USER)
        self.assertEqual(asset.asset_id, "u-1")
        self.assertEqual(asset.owner, "asha.rao@contoso.com")
        self.assertEqual(asset.status, AssetStatus.ENABLED)

    def test_normalize_device_picks_up_owner_and_os_tag(self):
        [asset] = normalize({"device": RAW["device"]})
        self.assertEqual(asset.asset_type, AssetType.DEVICE)
        self.assertEqual(asset.owner, "asha.rao@contoso.com")
        self.assertIn("windows", asset.tags)

    def test_normalize_domain_uses_id_as_display_name(self):
        [asset] = normalize({"domain": RAW["domain"]})
        self.assertEqual(asset.display_name, "contoso.com")
        self.assertEqual(asset.status, AssetStatus.ENABLED)

    def test_normalize_unknown_resource_raises(self):
        with self.assertRaises(NormalizationError):
            normalize({"unknown_resource": [{"id": "x"}]})

    def test_normalize_findings_maps_audit_log_entry(self):
        [finding] = normalize_findings(RAW_AUDIT_LOG)
        self.assertEqual(finding.finding_id, "al-1")
        self.assertEqual(finding.finding_type, "audit_log")
        self.assertEqual(finding.activity, "Add user")
        self.assertEqual(finding.actor, "admin@contoso.com")
        self.assertEqual(finding.target, "Devon Lee")
        self.assertEqual(finding.result, "success")

    def test_normalize_findings_skips_asset_type_resources(self):
        # Only "audit_log" (or other finding-type resources) should produce
        # Findings; asset-type resources should be skipped, not raise.
        findings = normalize_findings(RAW)
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
