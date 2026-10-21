#!/usr/bin/env bash
set -euo pipefail

KEYS_FILE="${VAULT_KEYS_FILE:-$HOME/.vault/vault_keys.txt}"
export VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"

if ! command -v vault >/dev/null 2>&1; then
    echo "Error: Vault CLI is not installed or not in PATH."
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "Error: jq is not installed or not in PATH."
    exit 1
fi

if [ ! -f "$KEYS_FILE" ]; then
    echo "Error: Key file not found at the configured external path."
    echo "Set VAULT_KEYS_FILE to the secure location of your key file."
    exit 1
fi

echo "Checking Vault status at $VAULT_ADDR..."

STATUS_RC=0
STATUS_JSON=$(vault status -format=json 2>/dev/null) || STATUS_RC=$?

if [ "$STATUS_RC" -ne 0 ] && [ "$STATUS_RC" -ne 2 ]; then
    echo "Error: Could not retrieve Vault status. Check connectivity and permissions."
    exit 1
fi

IS_SEALED=$(printf '%s' "$STATUS_JSON" | jq -r '.sealed')

if [ "$IS_SEALED" = "false" ]; then
    echo "Vault is already unsealed."
    exit 0
fi

if [ "$IS_SEALED" != "true" ]; then
    echo "Error: Could not determine Vault seal status."
    exit 1
fi

echo "Vault is sealed. Reading unseal keys from the configured external file..."

UNSEAL_KEYS=$(grep -i "Unseal Key" "$KEYS_FILE" | awk '{print $NF}' || true)

if [ -z "$UNSEAL_KEYS" ]; then
    echo "Error: No unseal keys were found in the configured file."
    exit 1
fi

while IFS= read -r KEY; do
    [ -n "$KEY" ] || continue

    echo "Applying unseal key..."
    if ! UNSEAL_RESPONSE=$(vault operator unseal -format=json "$KEY" 2>/dev/null); then
        unset KEY UNSEAL_KEYS
        echo "Error: Vault rejected an unseal operation."
        exit 1
    fi
    unset KEY

    SEALED_STATUS=$(printf '%s' "$UNSEAL_RESPONSE" | jq -r '.sealed')

    if [ "$SEALED_STATUS" = "false" ]; then
        echo "Successfully unsealed Vault!"
        unset UNSEAL_KEYS
        exit 0
    fi

    PROGRESS=$(printf '%s' "$UNSEAL_RESPONSE" | jq -r '.progress // .t // "unknown"')
    THRESHOLD=$(printf '%s' "$UNSEAL_RESPONSE" | jq -r '.n // "unknown"')
    echo "Unseal progress: $PROGRESS / $THRESHOLD"
done <<< "$UNSEAL_KEYS"

unset UNSEAL_KEYS
echo "Vault remains sealed. More valid unseal keys may be required."
exit 1
