import string
import pytest
from unittest.mock import patch

from utils import (
    generate_short_code,
    hash_password,
    verify_password,
    create_access_token,
)
from config import settings

class TestGenerateShortCode:
    def test_default_length_is_six(self):
        code = generate_short_code()
        assert len(code) == 6

    def test_custom_length_four(self):
        code = generate_short_code(4)
        assert len(code) == 4

    def test_custom_length_twelve(self):
        code = generate_short_code(12)
        assert len(code) == 12

    def test_characters_are_alphanumeric(self):
        allowed = set(string.ascii_letters + string.digits)
        for _ in range(50):
            code = generate_short_code()
            assert all(c in allowed for c in code), f"Invalid chars in: {code}"

    def test_generates_different_codes_across_calls(self):
        codes = {generate_short_code() for _ in range(200)}
        assert len(codes) > 1

    def test_zero_length_returns_empty_string(self):
        assert generate_short_code(0) == ""

class TestPasswordHashing:
    def test_hash_returns_string(self):
        assert isinstance(hash_password("secret"), str)

    def test_hash_differs_from_plaintext(self):
        pw = "my_password"
        assert hash_password(pw) != pw

    def test_hash_uses_bcrypt_prefix(self):
        assert hash_password("test").startswith("$2")

    def test_two_hashes_of_same_password_differ(self):
        pw = "same_password"
        assert hash_password(pw) != hash_password(pw)

    def test_verify_correct_password(self):
        pw = "correct_horse_battery_staple"
        assert verify_password(pw, hash_password(pw)) is True

    def test_verify_wrong_password(self):
        assert verify_password("wrong", hash_password("right")) is False

    def test_verify_empty_password_against_hash(self):
        assert verify_password("", hash_password("notempty")) is False

class TestCreateAccessToken:
    def test_returns_non_empty_string(self):
        token = create_access_token({"sub": "user@example.com"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_has_three_jwt_parts(self):
        token = create_access_token({"sub": "user@example.com"})
        assert len(token.split(".")) == 3

    def test_token_contains_subject(self):
        from jose import jwt
        email = "alice@wonderland.com"
        token = create_access_token({"sub": email})
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == email

    def test_token_contains_expiry(self):
        from jose import jwt
        token = create_access_token({"sub": "x@x.com"})
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert "exp" in payload

    def test_token_carries_extra_claims(self):
        from jose import jwt
        token = create_access_token({"sub": "x@x.com", "role": "admin"})
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload.get("role") == "admin"

    def test_different_data_produces_different_tokens(self):
        t1 = create_access_token({"sub": "a@a.com"})
        t2 = create_access_token({"sub": "b@b.com"})
        assert t1 != t2
