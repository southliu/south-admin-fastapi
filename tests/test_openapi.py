from main import app


def test_user_pagination_constraints_are_in_openapi() -> None:
    operation = app.openapi()["paths"]["/system/user/page"]["get"]
    parameters = {
        parameter["name"]: parameter for parameter in operation["parameters"]
    }

    assert parameters["page"]["schema"]["minimum"] == 1
    assert parameters["pageSize"]["schema"]["minimum"] == 1
    assert parameters["pageSize"]["schema"]["maximum"] == 100
