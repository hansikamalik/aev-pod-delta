#System Architecture & Data Flow 

#### **`ARCHITECTURE.md`**
```markdown
# System Architecture & Data Pipeline Flow

## High-Level Execution Sequence

```text
[ Raw Azure Event Payload ]
           │
           ▼
[ Resource Normalizer ] ──> Extracts tags, identities, metadata
           │
           ▼
[ CAM Schema Validator ] ──> Validates against contracts/azure_cam_schema.json
     │           │
   PASS         FAIL
     │           └──────────────────────────┐
     ▼                                      ▼
[ Platform Push Engine ]          [ Dead Letter Queue (DLQ) ]
  (Retry with Exponential Backoff)    (Local disk or storage dump)
