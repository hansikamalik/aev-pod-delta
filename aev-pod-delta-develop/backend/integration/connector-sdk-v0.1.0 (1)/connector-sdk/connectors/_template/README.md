# <source> Connector

Copy this directory to `connectors/<source>/` and replace the placeholders.

- **Asset types produced:** compute / storage / identity / ...
- **Sync mode:** full sync on every run *(or: incremental via `<cursor field>`)*
- **Pagination:** `<cursor / next-token / offset>`
- **Required config:** `<field>` — see `describe_config()`
- **Required credentials:** `<field>` — see `describe_credentials()`, resolved from Vault

## Run locally

```bash
pytest connectors/<source>/tests
```
