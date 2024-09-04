import os

import click
import uvicorn


def default_log_config():
    from importlib.resources import files
    return files('scancode_extensions.resources').joinpath('log_config.yaml')


@click.command()
@click.option('--workers', default=1, help="Number of parallel workers.")
@click.option('--log-config', default=default_log_config(), help="Configuration file for logging.")
@click.option('--port', default=8000, help="Port to accept connections.")
@click.version_option(package_name="scancode_service")
def start(log_config, workers, port):
    check_environment()

    uvicorn.run("scancode_extensions.service:app", host="0.0.0.0", port=port, workers=workers, log_config=log_config,
                timeout_graceful_shutdown=5)


def check_environment():
    scancode_temp_dir = os.getenv("SCANCODE_TEMP")
    scancode_cache_dir = os.getenv("SCANCODE_CACHE")
    licensecode_cache_dir = os.getenv("SCANCODE_LICENSE_INDEX_CACHE")

    if not scancode_temp_dir:
        raise ValueError(
            "Please set environment variable 'SCANCODE_TEMP'\n\texport SCANCODE_TEMP=/path/to/scancode/temp")

    if not scancode_cache_dir:
        raise ValueError(
            "Please set environment variable 'SCANCODE_CACHE'\n\texport SCANCODE_CACHE=/path/to/scancode/cache")

    if not licensecode_cache_dir:
        raise ValueError(
            "Please set environment variable 'SCANCODE_LICENSE_INDEX_CACHE'\n\texport SCANCODE_LICENSE_INDEX_CACHE=/path/to/index/cache")
