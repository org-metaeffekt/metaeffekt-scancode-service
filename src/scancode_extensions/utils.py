import asyncio
import functools
import logging
import os
import time
from pathlib import Path
from typing import Coroutine

log = logging.getLogger("scanservice")


def timings(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        log.info(f"Execution time for {callable_name()}: {end_time - start_time}")
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
        log.info(f"Execution time for {callable_name()}: {end_time - start_time}")
        return result

    if asyncio.iscoroutine(func):
        return async_wrapper
    return wrapper


def compute_scanroot_relative(filename, root):
    rel_root = str(Path(root).parent)
    relative = os.path.relpath(filename, rel_root)
    return relative
