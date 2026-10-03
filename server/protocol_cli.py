"""Entry point that preserves the caller's working directory."""
from mog_protocol.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
