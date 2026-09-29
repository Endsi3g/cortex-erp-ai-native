"""Send signed-in users to the standalone Cortex app (`/cortex`) unless another default app was chosen."""

from cortex_rental.auth_setup import ensure_default_app


def execute():
    ensure_default_app()
