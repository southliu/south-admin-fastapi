import yaml
from pathlib import Path

_config_path = Path(__file__).parent.parent / "config.yaml"

with open(_config_path, "r", encoding="utf-8") as f:
    _config = yaml.safe_load(f)

SECRET_KEY = _config["jwt"]["secret_key"]
ALGORITHM = _config["jwt"]["algorithm"]
ACCESS_TOKEN_EXPIRE_MINUTES = _config["jwt"]["access_token_expire_minutes"]

# 只读模式：为 1 时除登录外的非 GET 请求全部拒绝（ReadOnlyMiddleware），其他值不生效
READONLY_ENABLED = int(_config.get("readonly", {}).get("enabled", 0))
