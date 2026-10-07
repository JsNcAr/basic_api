"""
Configuration rules that need no database.
"""

import pytest

from basic_api import config
from basic_api.config import csv_list, docs_enabled


@pytest.mark.parametrize(
    "environment, enable_docs, expected",
    [
        ("development", None, True),
        ("staging", None, True),
        ("production", None, False),
        ("production", "true", True),
        ("production", "1", True),
        ("development", "false", False),
        ("development", "", True),
    ],
)
def test_docs_are_off_in_production_unless_enabled(environment, enable_docs, expected):
    assert docs_enabled(environment, enable_docs) is expected


def test_csv_settings_are_trimmed_and_empties_dropped():
    assert csv_list("a, b ,,c") == ["a", "b", "c"]
    assert csv_list("*") == ["*"]


def test_under_pytest_the_database_url_targets_the_test_database():
    # The app's own engine must point at the same database the fixtures use,
    # or the health check would answer 503 in CI.
    assert config.DATABASE_URL.startswith("postgresql+asyncpg://")
    assert (
        config.DATABASE_URL.rsplit("/", 1)[-1]
        == config._test_database_url().rsplit("/", 1)[-1]
    )


def test_app_version_is_a_version_string():
    assert config.APP_VERSION and config.APP_VERSION[0].isdigit()
