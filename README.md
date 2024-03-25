# Scancode Extensions

Scancode Extensions or Scancode Service is a small package to extend Scancode Toolkit. At the heart of the package is a
web service that can answer any number of scan requests after launch.

## Building

Use pythons build frontend for packaging. Call from the project directory

```bash
python -m build
```

This will build a python wheel that can be installed by pip, for example.

## Installing

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

## Usage

```bash
scancode-service
```

This will start the service. At [http://localhost:8000/docs](http://localhost:8000/docs) you will find a documentation
of the API.
Scan requests can be initiated by a post request to [http://localhost:8000/scan](http://localhost:8000/scan). For the
status
of the service and an overview over the current scans send a get request
to [http://localhost:8000/scan](http://localhost:8000/scan).