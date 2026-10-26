# Architecture & Data Flow

## Data Flow Pipeline

```text
[ Discovery Targets ] 
   │ (LDAP / AWS / Azure / API)
   ▼
[ Discovery Module ] ───> Extracts Raw Discovered Accounts
   │
   ▼
[ Normalization Module ] 
   │ ├── Validator    ───> Filters out excluded accounts/hosts
   │ └── Transformer  ───> Maps OS/Platform to CyberArk Schema
   ▼
[ Push Module ] 
   │ ├── CyberArk Client ─> Authenticates via PVWA REST API
   │ └── Onboarder       ─> Bulk dispatches to CyberArk Pending Accounts
   ▼
[ CyberArk PVWA ]
