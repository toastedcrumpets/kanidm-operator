from typing import TypedDict


class OAuth2ClientResource(TypedDict):
    name: str
    displayName: str
    origin: str | None
    kanidmName: str
