import base64
import os

class SimpleCipher:
    """Utility for light encoding/decoding of runtime parameters."""

    @staticmethod
    def encrypt(raw_str: str) -> str:
        if not raw_str:
            return ""
        return base64.b64encode(raw_str.encode("utf-8")).decode("utf-8")

    @staticmethod
    def decrypt(enc_str: str) -> str:
        if not enc_str:
            return ""
        return base64.b64decode(enc_str.encode("utf-8")).decode("utf-8")

    @staticmethod
    def get_env_secret(env_var_name: str, default: str = "") -> str:
        return os.getenv(env_var_name, default)
