FROM python:3.13-slim

ARG INSTALL_EXTRAS=aws,spark,dbt

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DAGSTER_HOME=/opt/dagster/dagster_home \
    DAGSTER_GRPC_PORT=4000 \
    DAGSTER_MODULE_NAME=dagster_user_code.definitions \
    JAVA_HOME=/usr/lib/jvm/default-java \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local

WORKDIR /opt/dagster/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        default-jre-headless \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN set -eux; \
    extra_flags=""; \
    OLD_IFS="$IFS"; \
    IFS=','; \
    for extra in $INSTALL_EXTRAS; do \
        extra_flags="$extra_flags --extra $extra"; \
    done; \
    IFS="$OLD_IFS"; \
    uv sync --frozen --no-dev $extra_flags

RUN mkdir -p "${DAGSTER_HOME}"

EXPOSE 4000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import dagster_user_code.bootstrap"

ENTRYPOINT ["tini", "--"]
CMD ["sh", "-c", "dagster api grpc -h 0.0.0.0 -p ${DAGSTER_GRPC_PORT} -m ${DAGSTER_MODULE_NAME}"]
