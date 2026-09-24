# Splunk Connector

Standalone Splunk Enterprise/Cloud integration connector.

## Directory Structure
- `client.py`: Splunk REST API Client (Auth, Searches, Retries, Errors)
- `config.py`: Schema configuration with HashiCorp Vault compliance
- `connector.py`: Main `SplunkConnector` logic
- `models.py`: Event normalization & secret scrubbing
- `connector_sdk/`: Embedded SDK base classes (`Connector`, `Asset`, `Checkpoint`)
- `tests/`: Complete unit and integration test suite

## Testing
Run unit and integration tests:
```bash
python3 -m pytest -v
