# [UAT DEFECT] {{ classification.severity }}: {{ failure.connector }} - {{ classification.category }}

- **Connector Target:** `{{ failure.connector }}`
- **Assigned Engineering Team:** `{{ owner }}`
- **Severity Level:** {{ classification.severity }}
- **Fix SLA:** {{ classification.priority }}
- **Source:** `{{ failure.source }}`

---

### Executive Summary
{{ classification.summary }}

{% if vault_check.has_leak %}
> **SECURITY WARNING:** Vault Audit Check failed. Unredacted credential tokens detected in log trace:
{% for leak in vault_check.leaked_tokens %}
> - **Key:** `{{ leak.token_key }}` | **Masked Sample:** `{{ leak.sample }}`
{% endfor %}
{% endif %}

---

### Execution Failure Details
```text
{{ failure.traceback }}
