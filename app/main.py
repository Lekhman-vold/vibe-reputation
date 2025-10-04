# Main entry point for the FastAPI application
# This file ensures backward compatibility with existing deployment scripts

from .api.main import app

__all__ = ['app']