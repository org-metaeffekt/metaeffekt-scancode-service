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

import asyncio
import functools
import logging
import os
import platform
import sys
import time
import uuid
from functools import wraps
from pathlib import Path
from typing import Coroutine

import commoncode

log = logging.getLogger("scanservice")


def timings(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        log.debug(f"Execution time for {callable_name()}: {end_time - start_time}")
        return result

    def callable_name():
        if isinstance(func, functools.partial):
            name = func.func.__name__
        else:
            name = func.__name__
        return name

    return wrapper

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        func: Coroutine
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        end_time = time.perf_counter()
        log.debug(f"Execution time for {callable_name()}: {end_time - start_time}")
        return result

    if asyncio.iscoroutine(func):
        return async_wrapper
    return wrapper


def compute_scanroot_relative(filename, root):
    rel_root = str(Path(root).parent)
    relative = os.path.relpath(filename, rel_root)
    return relative


def make_atomic(like_process_codebase, modifier=uuid.uuid4):
    """Wrap a function to modify its output_json_pp keyword arg to use a temporary file. This
    happens if and only if output_json_pp is passed as keyword arg.
    The temporary file is created in the output folder of the original file to enable an
    atomic rename after the function call.

    This implementation is inspired by https://alexwlchan.net/2019/atomic-cross-filesystem-moves-in-python/
    """

    @wraps(like_process_codebase)
    def wrapper(*args, **kwargs):
        if "output_json_pp" in kwargs:
            dst = kwargs.pop("output_json_pp")
            copy_id = modifier()
            tmp_dst = "%s.%s.tmp" % (dst, copy_id)
            result = like_process_codebase(*args, output_json_pp=tmp_dst, **kwargs)
            os.rename(tmp_dst, dst)
            return result
        return like_process_codebase(*args, **kwargs)

    return wrapper


def get_system_environment():
    return {
        'operating_system': commoncode.system.current_os,
        'cpu_architecture': commoncode.system.current_arch,
        'platform': platform.platform(),
        'platform_version': platform.version(),
        'python_version': sys.version
    }
