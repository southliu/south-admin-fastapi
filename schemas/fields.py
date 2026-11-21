from typing import Annotated

from pydantic import AfterValidator, Field


def validate_password_bytes(value: str) -> str:
    """Enforce bcrypt's byte limit before hashing or verification."""
    if len(value.encode("utf-8")) > 72:
        raise ValueError("密码不能超过 72 个 UTF-8 字节")
    return value


def validate_text_bytes(value: str) -> str:
    """Match MySQL TEXT's byte capacity for multibyte input."""
    if len(value.encode("utf-8")) > 65535:
        raise ValueError("文本不能超过 65535 个 UTF-8 字节")
    return value


Password = Annotated[
    str,
    Field(min_length=8, max_length=72),
    AfterValidator(validate_password_bytes),
]
TextContent = Annotated[
    str, Field(max_length=65535), AfterValidator(validate_text_bytes)
]
Description = TextContent
