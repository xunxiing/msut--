from typing import TypedDict, Optional


class JWTPayload(TypedDict, total=False):
    uid: int
    username: str
    iat: int
    exp: int
