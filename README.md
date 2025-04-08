# metaeffekt-scancode-service

The metaeffekt-scancode-service is a service using and extendind the AboutCode ScanCode Toolkit. At the core 
metaeffekt-scancode-service package is a web service that can answer any number of scan requests after launch.

Using the ScanCode Toolkit on command-line-level comes with a certain penalty for bootstrapping the scan. To avoid
these costs a local service is established that performs the bootstrapping on startup and then can happily can be used
to execute scans on the local filesystem.

Furthermore, we activate/add some features of ScanCode that are otherwise not easily accessible:
* Including all rights reserved in copyright statements
* Preserve punctuation in copyright statements

## Building
This project uses a modern `pyproject.toml`. You can use it with any compatible packaging tool.
I.e. use pythons build frontend for packaging. Call from the project directory

```bash
python -m build
```

or

```bash
python3 -m build
```

This will build a python wheel that can be installed by pip, for example.

***Please note that in some systems python3 must be called not with the `python` command but with `python3`.***

## Installation

It's recommended to install into a virtual environment. Either use

```bash
python -m venv scancode-extensions
source scancode-extensions/bin/activate
python -m pip install WHEEL_FILE
```

or if you have pipx installed, use

```bash
python -m pipx install WHEEL_FILE 
```
or

```bash
pipx install WHEEL_FILE --force
```

## Usage
### Configure Cache and Temporary Directories
The service requires that a few environment variables are set. At startup, it checks if these variables exist.
If not the service refuses to start. The variables configure the paths for ScanCode Toolkits cache, index cache 
and temporary files.
To configure these use
```bash
export SCANCODE_TEMP=/var/opt/scancode/temp
export SCANCODE_CACHE=/var/opt/scancode/cache
export SCANCODE_LICENSE_INDEX_CACHE=/var/opt/scancode/lcache
```

Recommended configuration on macOS:
```bash
export SCANCODE_TEMP=/var/tmp/scancode/temp
export SCANCODE_CACHE=/var/tmp/scancode/cache
export SCANCODE_LICENSE_INDEX_CACHE=/var/tmp/scancode/lcache
```

You can use any paths you want. We would recommend to use different directories for each of these.

### Configure the Number of Threads Used
To configure the number of threads used to scan the given input files there is an environment variable.
The following line configures the service to use 6 processes in parallel, which is the default.
```bash
export SCANCODE_SERVICE_PROCESSES=6
```

## Docker
Build the image with
```shell
docker build -t scancode-service .
```
and start the container
```shell
docker run -p 8000:8000 --mount type=bind,source=/metaeffekt-scancode-toolkit/tests/cluecode/data/,target=/metaeffekt-scancode-toolkit/tests/cluecode/data/ scancode-service
```
It is important to bind mount the scan directory exactly to the same location into the container as on the host.
### Start the Service
Type
```bash
scancode-service
```

which will start the service. 

At [http://localhost:8000/docs](http://localhost:8000/docs) you will find a documentation of the API. Scan requests can be initiated by a 
post request to [http://localhost:8000/scan](http://localhost:8000/scan). For the  status of the service and an overview over the current 
scans send a get request to [http://localhost:8000/scan](http://localhost:8000/scan).

### Run as Systemd Service
Given one has installed Scancode Extensions into `/var/opt/scancode-service` with permissions for user `scancode`.
The following example configuration could help to start it as a systemd service.

Create file `/etc/systemd/system/metaeffekt-scancode.service` with the following content.

```shell
[Unit]
Description=metaeffekt scancode service
## make sure we only start the service after network is up
Wants=network-online.target
After=network.target

[Service]
## here we can set custom environment variables
Environment=SCANCODE_TEMP=/var/opt/scancode/temp
Environment=SCANCODE_CACHE=/var/opt/scancode/cache
Environment=SCANCODE_LICENSE_INDEX_CACHE=/var/opt/scancode/lcache
Environment=UVICORN_LOG_CONFIG=/var/opt/scancode/logging.yaml
Type=notify
ExecStart=/opt/metaeffekt/scancode/scancode-service.sh --log-config /opt/metaeffekt/scancode/logging.yaml
WatchdogSec=60
Restart=on-watchdog
User=scancode
NotifyAccess=all

# Useful during debugging; remove it once the service is working
StandardOutput=journal

[Install]
WantedBy=multi-user.target
```

Next create `/opt/metaeffekt/scancode/scancode-service.sh` and insert the following.

```shell
#!/usr/bin/env bash

CONNECT_TIMEOUT=${HTTP_CONNECT_TIMEOUT:-1}
HTTP_ADDR=${FILEBEAT_HTTP_ADDR:-http://localhost:8000/scan}
REPORT_TIME=$(($WATCHDOG_USEC / 2000000))
SD_NOTIFY=${SD_NOTIFY_PATH:-/bin/systemd-notify}

set -euo pipefail

function watchdog() {
    READY=0
    sleep $(echo $REPORT_TIME*1.5 | bc)

    while true ; do
        info=$(curl -fs --connect-timeout "${CONNECT_TIMEOUT}" "${HTTP_ADDR}")
        beat=$(echo "${info}" | jq -r .status)
        current_scans=$(echo "${info}" | jq -r .scans)
        if [[ $? == 0 ]] ; then
            if [[ $READY == 0 ]] ; then
                "${SD_NOTIFY}" --ready
                READY=1
            fi

            "${SD_NOTIFY}" WATCHDOG=1
            "${SD_NOTIFY}" STATUS="metaeffekt-scancode-service is ${beat}. Active scans: ${current_scans}."
        else
            "${SD_NOTIFY}" WATCHDOG=trigger
            "${SD_NOTIFY}" STATUS=Beat not responding
            exit 1
        fi

        sleep ${REPORT_TIME}
    done
}

watchdog &

exec /opt/metaeffekt/scancode/venv/bin/scancode-service "$@"
```

With `sudo systemctl start metaeffekt-scancode` you could start the service. `sudo systemctl status metaeffekt-scancode` 
returns the current status of the service.

# License
The original ScanCode Toolkit code is licensed under Apache License 2.0. The modification, extensions and configuration
of the metaeffekt-scancode-service are also provided under Apache License 2.0. Please see the [LICENSE](LICENSE) and 
[NOTICE](NOTICE) file for details.
