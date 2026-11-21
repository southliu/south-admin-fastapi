import pytest
from pydantic import ValidationError

from config.settings import Settings
from schemas.menu import UpdateMenuRequest
from schemas.role import UpdateRoleRequest
from schemas.user import CreateUserRequest, UpdateUserRequest


@pytest.mark.parametrize(
    "changes",
    [
        {"password": "short"},
        {"email": "not-an-email"},
        {"status": 2},
        {"role_ids": [0]},
    ],
)
def test_create_user_rejects_invalid_values(
    changes: dict[str, object],
) -> None:
    data: dict[str, object] = {
        "username": "admin",
        "password": "safe-password",
        "email": "admin@example.com",
        "status": 1,
        "role_ids": [1],
    }
    data.update(changes)

    with pytest.raises(ValidationError):
        CreateUserRequest.model_validate(data)


def test_production_rejects_example_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database={"url": "mysql+aiomysql://localhost/test"},
            jwt={"secret_key": "your-secret-key-here"},
        )


@pytest.mark.parametrize(
    ("schema", "data"),
    [
        (
            UpdateUserRequest,
            {"username": "user", "status": 1},
        ),
        (
            UpdateRoleRequest,
            {"name": "editor"},
        ),
        (
            UpdateMenuRequest,
            {"label": "菜单", "label_en": "Menu"},
        ),
    ],
)
def test_put_schemas_require_complete_non_nullable_fields(
    schema: type,
    data: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate(data)


def test_settings_rejects_unapproved_jwt_algorithm() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="test",
            database={"url": "mysql+aiomysql://localhost/test"},
            jwt={
                "secret_key": "long-enough-test-secret",
                "algorithm": "none",
            },
        )
