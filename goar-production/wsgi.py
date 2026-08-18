"""WSGI entry point for the GOAR Flask service."""

from goar import create_flask_app

application = create_flask_app()

__all__ = ["application"]
