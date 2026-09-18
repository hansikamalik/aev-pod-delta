vault {
  address = "http://127.0.0.1:8200"
}

auto_auth {
  method "approle" {
    config = {
      role_id_file_path   = "role_id"
      secret_id_file_path = "secret_id"
      remove_secret_id_file_after_reading = false
    }
  }

  sink {
    type = "file"
    config = {
      path = "vault_token"
    }
  }
}

template {
  source      = "application/config.env.tmpl"
  destination = "application/config.env"
}

pid_file = "./vault-agent.pid"
