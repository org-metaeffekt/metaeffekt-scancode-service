#  Copyright 2021-2026 the original author or authors.
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
import logging
from dataclasses import dataclass
from datetime import datetime

log = logging.getLogger("task_monitor")

tasks: dict = dict()

@dataclass
class TaskInfo:
    uuid: str
    started_at: datetime
    location: str
    relative_path: str

def put_task(id: str, info: TaskInfo) -> None:
    tasks[id] = info

def remove_task(id: str) -> TaskInfo:
    return tasks.pop(id)

def get_all() -> dict[str, TaskInfo]:
    return tasks

def remove_all_tasks(uuid: str) -> None:
    for k in list(tasks.keys()):
        if tasks[k].uuid == uuid:
            log.debug(f"Removing task {tasks[k]} with id {k}.")
            del tasks[k]