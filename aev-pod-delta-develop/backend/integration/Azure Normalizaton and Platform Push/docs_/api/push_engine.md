#Push Engine & DLQ Configuration 

#### **`docs/api/push_engine.md`**
```markdown
# Push Engine & DLQ Specification

The `PlatformPushEngine` (`src/push/platform_pusher.py`) transmits records to the target platform API and falls back to `DLQHandler` (`src/push/dlq_handler.py`) on non-retriable failures.

```python
from src.push.platform_pusher import PlatformPushEngine

pusher = PlatformPushEngine(
    endpoint_url="[https://api.example.com/push](https://api.example.com/push)",
    api_key="secret-key",
    max_retries=3,
    backoff_factor=1.5
)

# Pushes batch and automatically routes failures to DLQ
response = pusher.push_batch(validated_records)
