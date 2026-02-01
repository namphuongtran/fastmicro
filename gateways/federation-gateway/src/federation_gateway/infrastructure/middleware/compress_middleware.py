import logging

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

logger = logging.getLogger(__name__)

def setup_compress_middleware(app: FastAPI):
    """
    Setup GZip middleware for FastAPI application.
    
    Args:
        app: FastAPI application instance
    """

    # Add GZip middleware to FastAPI
    # Handles GZip responses for any request that includes "gzip" in the Accept-Encoding header.
    # https://fastapi.tiangolo.com/advanced/middleware/#gzipmiddleware
    app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)

    logger.info("GZip middleware configured with minimum size 1000 bytes and compress level 5")
