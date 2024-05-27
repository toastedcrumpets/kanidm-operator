from typing import TypedDict


class UserResource(TypedDict):
    kanidmName: str
    name: str
    displayName: str
    emails: list[str] | None
