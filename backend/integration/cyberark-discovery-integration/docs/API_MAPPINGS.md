#### `docs/API_MAPPINGS.md`
```markdown
# API Field Mapping Matrix

| Raw Source Attribute | Normalized Field | CyberArk Target Attribute | Mapping Rule / Example |
| :--- | :--- | :--- | :--- |
| `raw_account_name` | `userName` | `userName` | Lowercase trimmed string (`svc_sql_admin`) |
| `host_address` | `address` | `address` | FQDN or IP string (`10.0.10.45`) |
| `operating_system` | `platformId` | `platformID` | Rule lookup (e.g., `RHEL` -> `UnixSSH`) |
| `account_type` | `accountCategory` | `accountType` | Standardized category string |
| N/A | `safeName` | `safeName` | Default target safe (`Discovered_Accounts`) |
