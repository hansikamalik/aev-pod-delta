``markdown
# Troubleshooting Guide

| HTTP Status Code / Error | Root Cause | Resolution |
| :--- | :--- | :--- |
| **HTTP 401 Unauthorized** | Expired or invalid PVWA session token. | Check `CYBERARK_USER` and `CYBERARK_PASS` env variables. |
| **HTTP 403 Forbidden** | User lacks permissions to append to Pending Accounts. | Assign "Add Accounts" permission on target Safe. |
| **HTTP 409 Conflict** | Account already exists in Pending Accounts or Vault. | Expected for duplicate discovery runs. Check logs. |
| **`SSLError`** | Custom CA or untrusted self-signed certificate on PVWA. | Update `ssl_verify` in `config/cyberark_config.yaml` or set `REQUESTS_CA_BUNDLE`. |
