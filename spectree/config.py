from enum import Enum
from typing import Dict, List, Optional

from pydantic import AnyUrl, BaseModel, BaseSettings, EmailStr, root_validator

from .models import SecurityScheme, Server
from .page import DEFAULT_PAGE_TEMPLATES


class ModeEnum(str, Enum):
    normal = "normal"
    strict = "strict"
    greedy = "greedy"


class Contact(BaseModel):
    name: str
    url: AnyUrl = ""
    email: EmailStr = ""


class License(BaseModel):
    name: str
    url: AnyUrl = ""


class Configuration(BaseSettings):
    # OpenAPI configurations
    title: str = "Service API Document"
    description: str = None
    version: str = "0.1.0"
    terms_of_service: AnyUrl = None
    contact: Contact = None
    license: License = None

    # SpecTree configurations
    path: str = "apidoc"
    filename: str = "openapi.json"
    openapi_version: str = "3.0.3"
    mode: ModeEnum = ModeEnum.normal
    page_templates = DEFAULT_PAGE_TEMPLATES
    annotations = False
    servers: Optional[List[Server]] = []
    security_schemes: Optional[List[SecurityScheme]] = None
    security: Dict = {}

    class Config:
        env_prefix = "spectree_"
        validate_assignment = True

    @root_validator(pre=True)
    def convert_to_lower_case(cls, values):
        return {k.lower(): v for k, v in values.items()}

    @property
    def spec_url(self) -> str:
        return f"/{self.path}/{self.filename}"
