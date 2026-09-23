---

## `docs/usage.md`
```markdown
# Usage Examples & Production Workflows

## Workflow 1: Fetching Secrets via CCP with Custom Error Handling

```python
import logging
from src import CCPClient, CCPFetchError

logging.basicConfig(level=logging.INFO)

try:
    ccp = CCPClient(ccp_url="[https://ccp.internal.company.com](https://ccp.internal.company.com)", app_id="App_Linux_Pipeline")
    account = ccp.get_credential(safe="PAM_Linux_Keys", object_name="OperatingSystem-Linux-root")
    
    password = account["Content"]
    print("Successfully retrieved root password.")
    
except CCPFetchError as err:
    logging.error(f"Failed to fetch secret from CCP: {err}")
