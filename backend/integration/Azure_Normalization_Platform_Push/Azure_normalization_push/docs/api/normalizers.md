#Normalizers Spec & Schema 

#### **`docs/api/normalizers.md`**
```markdown
# Normalizer Specs & Supported Resource Types

All normalizers derive from `src.interfaces.base_normalizer.BaseNormalizer`.

| Resource Type | Provider Namespace | Normalizer Module |
| :--- | :--- | :--- |
| **Virtual Machines** | `Microsoft.Compute/virtualMachines` | `src/normalizers/vm.py` |
| **Storage Accounts** | `Microsoft.Storage/storageAccounts` | `src/normalizers/storage.py` |
| **Entra ID Users** | `Microsoft.Graph/users` | `src/normalizers/aad.py` |
| **SQL Databases** | `Microsoft.Sql/servers/databases` | `src/normalizers/sql.py` |
| **Function Apps** | `Microsoft.Web/sites` | `src/normalizers/functions.py` |
