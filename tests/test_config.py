from config import validate_config


def test_validate_config_ok():
    errors = validate_config()
    assert isinstance(errors, list)
    assert errors == []
