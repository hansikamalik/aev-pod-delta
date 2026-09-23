from src.utils.cipher import SimpleCipher
def test_cipher_encode_decode():
    secret = "CyberArkVault2026!"
    encrypted = SimpleCipher.encrypt(secret)
    assert encrypted != secret
    assert SimpleCipher.decrypt(encrypted) == secret

def test_cipher_empty_inputs():
    assert SimpleCipher.encrypt("") == ""
    assert SimpleCipher.decrypt("") == ""

def test_cipher_env_secret(monkeypatch):
    monkeypatch.setenv("EXISTING_SECRET_VAR", "my_secret_token")
    val = SimpleCipher.get_env_secret("EXISTING_SECRET_VAR", default="fallback")
    assert val == "my_secret_token"

    val_default = SimpleCipher.get_env_secret("MISSING_SECRET_VAR", default="fallback_value")
    assert val_default == "fallback_value"
