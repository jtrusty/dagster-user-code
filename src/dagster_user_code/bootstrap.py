from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from urllib.parse import urlparse

import boto3

LOGGER = logging.getLogger(__name__)
DEFAULT_INSTALL_DIR = "/opt/dagster/external-packages"
DEFAULT_MODULE = "stock_screener.dagster_defs"
WHEEL_VERSION_RE = re.compile(r"(?P<distribution>.+)-(?P<version>[^-]+)-")


def configured_pointer_uri() -> str:
    pointer_uri = os.getenv("DAGSTER_PACKAGE_CURRENT_URI", "").strip()
    if not pointer_uri:
        raise RuntimeError("DAGSTER_PACKAGE_CURRENT_URI must be set")
    return pointer_uri


def configured_module() -> str:
    module_name = os.getenv("DAGSTER_PACKAGE_MODULE", DEFAULT_MODULE).strip()
    if not module_name:
        raise RuntimeError("DAGSTER_PACKAGE_MODULE must be set")
    return module_name


def install_dir() -> Path:
    return Path(os.getenv("DAGSTER_PACKAGE_INSTALL_DIR", DEFAULT_INSTALL_DIR))


def marker_path(target_dir: Path) -> Path:
    return target_dir / ".dagster-package-wheel-uri"


def parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path:
        raise RuntimeError(f"Expected S3 URI, got: {uri}")
    return parsed.netloc, parsed.path.lstrip("/")


def s3_client():
    endpoint_url = os.getenv("AWS_ENDPOINT_URL") or os.getenv("S3_ENDPOINT_URL") or "https://s3.selfsvc.net"
    return boto3.client("s3", endpoint_url=endpoint_url)


def read_text_from_s3(uri: str) -> str:
    bucket, key = parse_s3_uri(uri)
    response = s3_client().get_object(Bucket=bucket, Key=key)
    return response["Body"].read().decode("utf-8").strip()


def download_wheel(uri: str, target_dir: Path) -> Path:
    bucket, key = parse_s3_uri(uri)
    target_dir.mkdir(parents=True, exist_ok=True)
    wheel_path = target_dir / Path(key).name
    s3_client().download_file(bucket, key, str(wheel_path))
    return wheel_path


def install_wheel(wheel_path: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--upgrade",
            "--target",
            str(target_dir),
            str(wheel_path),
        ],
        check=True,
    )


def inferred_distribution_from_wheel(wheel_uri: str) -> str | None:
    match = WHEEL_VERSION_RE.search(Path(urlparse(wheel_uri).path).name)
    if match:
        return match.group("distribution")
    return None


def inferred_version_from_wheel(wheel_uri: str) -> str | None:
    match = WHEEL_VERSION_RE.search(Path(urlparse(wheel_uri).path).name)
    if match:
        return match.group("version")
    return None


def log_bootstrap_metadata(pointer_uri: str, wheel_uri: str, wheel_path: Path, module_name: str) -> None:
    distribution_name = inferred_distribution_from_wheel(wheel_uri)
    try:
        installed_version = package_version(distribution_name) if distribution_name else None
    except PackageNotFoundError:
        installed_version = None

    payload = {
        "bootstrap_pointer_uri": pointer_uri,
        "configured_module": module_name,
        "resolved_wheel_uri": wheel_uri,
        "resolved_wheel_filename": wheel_path.name,
        "resolved_distribution_name": distribution_name,
        "resolved_distribution_version": inferred_version_from_wheel(wheel_uri),
        "installed_distribution_version": installed_version,
    }
    LOGGER.info("Loaded Dagster package release: %s", json.dumps(payload, sort_keys=True))


def ensure_package_installed() -> Path:
    target_dir = install_dir()
    if str(target_dir) not in sys.path:
        sys.path.insert(0, str(target_dir))

    pointer_uri = configured_pointer_uri()
    module_name = configured_module()
    wheel_uri = read_text_from_s3(pointer_uri)
    marker = marker_path(target_dir)
    if marker.exists() and marker.read_text(encoding="utf-8").strip() == wheel_uri:
        wheel_path = target_dir / ".artifacts" / Path(urlparse(wheel_uri).path).name
        log_bootstrap_metadata(pointer_uri, wheel_uri, wheel_path, module_name)
        return target_dir

    wheel_path = download_wheel(wheel_uri, target_dir / ".artifacts")
    install_wheel(wheel_path, target_dir)
    marker.write_text(f"{wheel_uri}\n", encoding="utf-8")
    log_bootstrap_metadata(pointer_uri, wheel_uri, wheel_path, module_name)
    return target_dir
