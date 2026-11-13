"""Allow ``python -m hlsdl`` to run the GUI and ``python -m hlsdl.cli`` the CLI."""

from .app import main

if __name__ == "__main__":
    raise SystemExit(main())
