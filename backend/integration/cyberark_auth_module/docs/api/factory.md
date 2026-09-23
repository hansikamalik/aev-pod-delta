# API Reference: CyberArkAuthFactory

The `CyberArkAuthFactory` provides a dynamic entry point for instantiating authenticators without directly importing concrete classes.

## Interface Signature

```python
class CyberArkAuthFactory:
    @classmethod
    def register_authenticator(cls, auth_type: str, authenticator_cls: Type[BaseAuthenticator]) -> None: ...
    
    @classmethod
    def create(cls, auth_type: str, **kwargs) -> BaseAuthenticator: ...
