import pytest

from tests.fake_pocketbase import FakePocketBase


@pytest.fixture
def fake_pb() -> FakePocketBase:
    return FakePocketBase()

