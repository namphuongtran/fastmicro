from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.cors import CORSMiddleware
from multiprocessing import cpu_count, freeze_support
import uvicorn

app_name = """Federation Gateway Service"""
app_version = "1.0.0"
description = """
This service acts as a central authentication gateway using standard OIDC (OpenID Connect) flows. 
It allows seamless integration with external identity providers (IdPs) such as Keycloak, Auth0, Entra ID, and others. 
The gateway handles user authentication, token exchange, and session management, making it easy to plug in different IdPs without changing your core application logic."""

# Create the main FastAPI application
app = FastAPI(title=app_name, version=app_version, description=description)

# Add middlewares and routers
# if security_config.cors.enabled:
#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=security_config.cors.allow_origins,
#         allow_credentials=security_config.cors.allow_credentials,
#         allow_methods=security_config.cors.allow_methods,
#         allow_headers=security_config.cors.allow_headers,
#     )

# Handles GZip responses for any request that includes "gzip" in the Accept-Encoding header.
# https://fastapi.tiangolo.com/advanced/middleware/#gzipmiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)

@app.get("/", include_in_schema=False)
async def root():
    """The root function is a default entrypoint for the application.

    Returns:
        _type_: _description_
    """
    return JSONResponse({"service": app_name, "version": app_version})

def run_server(host="127.0.0.1", port=9090, workers=4, loop="asyncio", reload=False):
    """Start to run the server"""
    uvicorn.run("src.main:app", host=host, port=port, workers=workers, loop=loop, reload=reload)


if __name__ == "__main__":
    freeze_support()  # Needed for pyinstaller for multiprocessing on WindowsOS
    num_workers = int(cpu_count() * 0.75)
    run_server(workers=num_workers)


