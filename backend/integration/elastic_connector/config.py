from pydantic import BaseModel, Field


class ElasticConfig(BaseModel):
    endpoint: str = Field(
        ...,
        description="Elasticsearch cluster HTTP/HTTPS URL endpoint (e.g. https://localhost:9200)"
    )
    timeout: int = Field(
        default=30,
        description="HTTP request timeout in seconds"
    )
    verify_ssl: bool = Field(
        default=True,
        description="Verify SSL/TLS certificates when making requests"
    )


class ElasticCredentials(BaseModel):
    api_key: str = Field(
        ...,
        description="Elasticsearch API Key for authenticating API requests",
        json_schema_extra={"secret": True}
    )
