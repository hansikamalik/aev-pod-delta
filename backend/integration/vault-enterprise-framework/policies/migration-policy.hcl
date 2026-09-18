path "secret/data/cyberark_migrated/*" {
  capabilities = ["create", "update", "read", "delete", "list"]
}

path "secret/metadata/cyberark_migrated/*" {
  capabilities = ["list", "delete"]
}
