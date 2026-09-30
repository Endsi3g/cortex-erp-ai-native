"""Sign-in lands on the Desk again (the standalone /cortex app was removed)."""

from cortex_rental.auth_setup import clear_default_app


def execute():
    clear_default_app()
