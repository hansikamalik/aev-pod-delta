#!/usr/bin/env bash
set -e

KEYS_FILE="vault_keys.txt"
export VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"

if [ ! -f "$KEYS_FILE" ]; then
    echo "Error: $KEYS_FILE not found!"
    exit 1
fi

echo "Checking Vault status at $VAULT_ADDR..."

# Check if already unsealed
IS_SEALED=$(vault status -format=json 2>/dev/null | jq -r '.sealed // empty')

if [ "$IS_SEALED" == "false" ]; then
    echo "Vault is already unsealed."
    exit 0
fi

echo "Vault is sealed. Extracting keys from $KEYS_FILE..."

# Extract all unseal keys from the file using grep and awk
UNSEAL_KEYS=$(grep -i "Unseal Key" "$KEYS_FILE" | awk '{print $NF}')

if [ -z "$UNSEAL_KEYS" ]; then
    echo "Error: No unseal keys found in $KEYS_FILE."
    exit 1
fi

# Iterate over each key and apply until unsealed
for KEY in $UNSEAL_KEYS; do
    echo "Applying unseal key..."
    
    UNSEAL_RESPONSE=$(vault operator unseal -format=json "$KEY" 2>/dev/null)
    SEALED_STATUS=$(echo "$UNSEAL_RESPONSE" | jq -r '.sealed')

    if [ "$SEALED_STATUS" == "false" ]; then
        echo "Successfully unsealed Vault!"
        break
    else
        PROGRESS=$(echo "$UNSEAL_RESPONSE" | jq -r '.t')
        THRESHOLD=$(echo "$UNSEAL_RESPONSE" | jq -r '.n')
        echo "Unseal progress: $PROGRESS / $THRESHOLD"
    fi
done

# Extract and display root token login command if available
ROOT_TOKEN=$(grep -i "Initial Root Token" "$KEYS_FILE" | awk '{print $NF}')
if [ -n "$ROOT_TOKEN" ]; then
    echo ""
    echo "To log in, run:"
    echo "vault login $ROOT_TOKEN"
fi
