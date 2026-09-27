#!/usr/bin/env bash
set -e

# Dynamically inherit VAULT_ADDR or default to local HTTP
export VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"

echo "==> Target Vault Address: $VAULT_ADDR"

echo "==> Applying HCL Policies..."
vault policy write app-policy policies/app-policy.hcl
vault policy write migration-policy policies/migration-policy.hcl

echo "==> Enabling Secret Engines..."
vault secrets enable -version=2 -path=secret kv || true
vault secrets enable database || true

echo "==> Enabling Auth Engines..."
vault auth enable approle || true

echo "==> Configuring AppRole for Workloads..."
vault write auth/approle/role/enterprise-app \
    secret_id_ttl=60m \
    token_num_uses=10 \
    token_ttl=1h \
    token_max_ttl=4h \
    token_policies="app-policy"

echo "==> Configuring Dynamic PostgreSQL Engine..."
vault write database/config/app-postgres \
    plugin_name=postgresql-database-plugin \
    allowed_roles="app-readwrite" \
    connection_url="postgresql://{{username}}:{{password}}@127.0.0.1:5432/production_db?sslmode=disable" \
    username="vault_admin_user" \
    password="VaultAdminSecurePassword123!" \
    verify_connection=false || true

vault write database/roles/app-readwrite \
    db_name=app-postgres \
    creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
    default_ttl="1h" \
    max_ttl="24h" || true

echo "==> Vault Cluster Setup Completed Successfully."
