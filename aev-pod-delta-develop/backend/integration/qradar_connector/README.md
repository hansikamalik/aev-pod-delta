
# IBM QRadar Connector

SDK-compliant integration connector for discovering asset inventory from IBM QRadar REST API.

## Configuration & Credentials

### Configuration Schema (`describe_config`)
* `host` (Required, string): Hostname or IP address of the QRadar Console.
* `verify_ssl` (Optional, boolean): Default `true`. Set to `false` if using self-signed certificates.
* `api_version` (Optional, string): Default `19.0`. REST API version header.

### Credential Schema (`describe_credentials`)
* `sec_token` (Required, secret string): Authorized Service Security Token generated in QRadar Admin settings.

## Synchronization Mechanics
* **Type:** Full Synchronization.
* **Pagination:** Standard Range header pagination (`items=0-49`).
* **Normalization:** Maps QRadar asset items to SDK standard `AssetType` identifiers (`network`, `compute`, `detection`, or `other`).

## Running Tests
```bash
pytest tests/
