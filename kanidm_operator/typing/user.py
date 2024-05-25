from typing import TypedDict


class UserResource(TypedDict):
    name: str
    displayName: str
    legalName: str | None
    emails: list[str] | None
