FROM python:3.14-slim

ARG INSTALL_EXTRAS=aws,dbt,spark

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DAGSTER_HOME=/opt/dagster/dagster_home \
    DAGSTER_GRPC_PORT=4000 \
    DAGSTER_MODULE_NAME=dagster_user_code.definitions \
    JAVA_HOME=/usr/lib/jvm/default-java

WORKDIR /opt/dagster/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        default-jre-headless \
        tini \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml constraints.txt README.md ./
COPY src ./src

RUN pip install --upgrade pip \
    && pip install -c constraints.txt ".[${INSTALL_EXTRAS}]"

RUN mkdir -p "${DAGSTER_HOME}"

EXPOSE 4000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import dagster_user_code"

ENTRYPOINT ["tini", "--"]
CMD ["sh", "-c", "dagster api grpc -h 0.0.0.0 -p ${DAGSTER_GRPC_PORT} -m ${DAGSTER_MODULE_NAME}"]
