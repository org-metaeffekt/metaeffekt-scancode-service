# Scancode Extensions

Scancode Extensions or Scancode Service is a small package to extend Scancode Toolkit. At the heart of the package is a
web service that can answer any number of scan requests after launch.

## Building

Use pythons build frontend for packaging. Call from the project directory

```bash
python -m build
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
The service requires that a few environment variables are set. At startup, it checks if these variables exist.
If not the service refuses to start. The variables configure the paths for ScanCode Toolkits cache, index cache 
and temporary files.
To configure these use
```bash
export SCANCODE_TEMP=/var/opt/scancode/temp
export SCANCODE_CACHE=/var/opt/scancode/cache
export SCANCODE_LICENSE_INDEX_CACHE=/var/opt/scancode/lcache
```
You can use any paths you want. We would recommend to use different directories for each of these.

After that type
```bash
scancode-service
```

which will start the service. 

At [http://localhost:8000/docs](http://localhost:8000/docs) you will find a documentation
of the API.
Scan requests can be initiated by a post request to [http://localhost:8000/scan](http://localhost:8000/scan). For the
status
of the service and an overview over the current scans send a get request
to [http://localhost:8000/scan](http://localhost:8000/scan).
### Run as Systemd Service
Given one has installed Scancode Extensions into `/var/opt/scancode-service` with permissions for user `scancode`.
The following example configuration could help to start it as a systemd service.

Create file `/etc/systemd/system/scancode-service.service` with the following content.

```shell
[Unit]
Description=Scancode Http Service
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
ExecStart=/opt/scancode-service/scancode-service.sh --log-config /opt/scancode-service/logging.yaml
WatchdogSec=60
Restart=on-watchdog
User=scancode
NotifyAccess=all

# Useful during debugging; remove it once the service is working
StandardOutput=journal

[Install]
WantedBy=multi-user.target
```

Next create `/opt/scancode-service/scancode-service.sh` and insert the following.

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
            "${SD_NOTIFY}" STATUS="Scancode-service is ${beat}. Active scans: ${current_scans}."
        else
            "${SD_NOTIFY}" WATCHDOG=trigger
            "${SD_NOTIFY}" STATUS=Beat not responding
            exit 1
        fi

        sleep ${REPORT_TIME}
    done
}

watchdog &

exec /opt/scancode-service/venv/bin/scancode-service "$@"
```

With `sudo systemctl start scancode-service` you could start the service. `sudo systemctl status scancode-service` 
returns the current status of the service.
## Development

### Using tox

One can start the service from the root directory by using

```bash
tox -e start
```

This starts scancode-service with its default parameters.