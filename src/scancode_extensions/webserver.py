#  Copyright 2021-2025 the original author or authors.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

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


if __name__ == "__main__":
    uvicorn.run("scancode_extensions.service:app", host="0.0.0.0", port=8000, log_config=str(default_log_config()))