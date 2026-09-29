"""Brand, Google/GitHub keys (disabled) and access settings defaults: see auth_setup.py."""

from cortex_rental.auth_setup import ensure_access_settings, ensure_social_login_keys


def execute():
    ensure_social_login_keys()
    ensure_access_settings()
