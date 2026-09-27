ui            = true
disable_mlock = true

storage "raft" {
  path    = "/var/lib/vault/data"
  node_id = "vault-node-01"
}

listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = "true"
}

api_addr     = "http://127.0.0.1:8200"
cluster_addr = "http://127.0.0.1:8201"
