from pydantic import BaseModel, ConfigDict


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class CamelModel(BaseModel):
    """统一 camelCase 别名的基类"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
    )
