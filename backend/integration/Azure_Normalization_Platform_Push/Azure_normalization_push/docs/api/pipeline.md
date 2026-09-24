#Pipeline Orchestrator API Docs

# Pipeline Orchestrator API Guide

The `PipelineOrchestrator` inside `src/pipeline.py` links normalization, contract verification, and platform delivery.

```python
from src.pipeline import PipelineOrchestrator

orchestrator = PipelineOrchestrator(
    endpoint_url="[https://api.platform.example.com/v1/assets](https://api.platform.example.com/v1/assets)",
    api_key="your-platform-api-key",
    dlq_dir="./dlq_output"
)

# Process a single batch of raw Azure records
summary = orchestrator.process_batch(raw_azure_records)
print(f"Processed: {summary['pushed']}, Failed: {summary['dlq']}")
