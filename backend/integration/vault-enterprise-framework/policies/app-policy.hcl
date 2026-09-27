path "secret/data/cyberark_migrated/*" {
  capabilities = ["read", "list"]
}

path "database/creds/app-readwrite" {
  capabilities = ["read"]
}
