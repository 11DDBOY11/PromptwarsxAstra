from pydantic import BaseModel, Field


class StatusIn(BaseModel):
    status: str
    assignee: str | None = Field(None, max_length=80)
    note: str | None = Field(None, max_length=300)


class LoginIn(BaseModel):
    email: str
    password: str
