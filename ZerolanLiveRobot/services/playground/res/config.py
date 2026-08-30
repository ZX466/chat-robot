from pydantic import BaseModel, Field


class ResourceServerConfig(BaseModel):
    host: str = Field("127.0.0.1", description="The host address of the resource server. Use 0.0.0.0 to expose to network.")
    port: int = Field(8899, description="The port number of the resource server")