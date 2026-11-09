import re

_PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9]).{8,}$")


def validate_password(password: str) -> bool:
    return (
        len(password.encode("utf-8")) <= 72
        and _PASSWORD_PATTERN.fullmatch(password) is not None
    )
