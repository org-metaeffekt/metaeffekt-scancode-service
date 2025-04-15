FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS build-stage

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy


WORKDIR /app

RUN apt-get update \
        && apt-get install -y --no-install-recommends \
        libmagic1 \
        libc6-dev \
        gcc \
        && rm -rf /var/lib/apt/lists/*

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

ADD . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm

ENV SCANCODE_TEMP=/scancode/temp
ENV SCANCODE_CACHE=/scancode/cache
ENV SCANCODE_LICENSE_INDEX_CACHE=/scancode/lcache

RUN mkdir -p /scancode/{temp,cache,lcache}
EXPOSE 8000

RUN apt-get update \
        && apt-get install -y --no-install-recommends \
        libmagic1 \
        libgomp1 \
        && rm -rf /var/lib/apt/lists/*

COPY --from=build-stage --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH"
# COPY --from=build-stage /app/src /app/src
# COPY --from=build-stage /app/.venv /app/.venv
# COPY --from=build-stage /app/pyproject.toml /app/pyproject.toml


CMD ["scancode-service"]