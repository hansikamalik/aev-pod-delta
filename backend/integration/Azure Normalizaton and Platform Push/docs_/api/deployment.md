
#Azure Deployment & Environment Setup 

---

### **3. Operations & Setup Guides (`docs/`)**

#### **`docs/deployment.md`**
```markdown
# Azure Deployment & Setup Guide

## Required Environment Variables

Set the following environment variables before executing the pipeline in production:

```bash
export PLATFORM_ENDPOINT_URL="[https://your-platform-endpoint.com/api/v1/assets](https://your-platform-endpoint.com/api/v1/assets)"
export PLATFORM_API_KEY="your-api-key"
export DLQ_STORAGE_PATH="/var/log/azure_push_dlq"
export LOG_LEVEL="INFO"
