"""FastAPI application factory."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title='AI Developer Copilot Platform', version='1.0.0')
    return app


app = create_app()

