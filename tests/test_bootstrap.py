from __future__ import annotations

import io
import sys
import types
from pathlib import Path

import dagster_user_code
import pytest
from dagster_user_code import bootstrap


class FakeS3Client:
    def __init__(self, body: str = "", downloaded: list[tuple[str, str, str]] | None = None) -> None:
        self._body = body
        self._downloaded = downloaded if downloaded is not None else []

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, io.BytesIO]:
        return {"Body": io.BytesIO(self._body.encode("utf-8"))}

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        self._downloaded.append((bucket, key, filename))
        Path(filename).write_text("wheel", encoding="utf-8")


def test_configured_pointer_uri_requires_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DAGSTER_PACKAGE_CURRENT_URI", raising=False)

    with pytest.raises(RuntimeError, match="DAGSTER_PACKAGE_CURRENT_URI must be set"):
        bootstrap.configured_pointer_uri()


def test_configured_module_defaults_and_validates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DAGSTER_PACKAGE_MODULE", raising=False)
    assert bootstrap.configured_module() == bootstrap.DEFAULT_MODULE

    monkeypatch.setenv("DAGSTER_PACKAGE_MODULE", "   ")
    with pytest.raises(RuntimeError, match="DAGSTER_PACKAGE_MODULE must be set"):
        bootstrap.configured_module()


def test_install_dir_ignores_blank_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DAGSTER_PACKAGE_INSTALL_DIR", "   ")

    assert bootstrap.install_dir() == Path(bootstrap.DEFAULT_INSTALL_DIR)


@pytest.mark.parametrize(
    ("uri", "expected"),
    [
        ("s3://bucket-name/path/to/file.txt", ("bucket-name", "path/to/file.txt")),
        ("s3://bucket-name/wheels/pkg-1.2.3-py3-none-any.whl", ("bucket-name", "wheels/pkg-1.2.3-py3-none-any.whl")),
    ],
)
def test_parse_s3_uri(uri: str, expected: tuple[str, str]) -> None:
    assert bootstrap.parse_s3_uri(uri) == expected


@pytest.mark.parametrize(
    "uri",
    [
        "",
        "https://bucket/key",
        "s3:///missing-bucket",
        "s3://bucket",
    ],
)
def test_parse_s3_uri_rejects_invalid_values(uri: str) -> None:
    with pytest.raises(RuntimeError, match="Expected S3 URI"):
        bootstrap.parse_s3_uri(uri)


def test_read_text_from_s3_rejects_empty_pointer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap, "s3_client", lambda: FakeS3Client("   "))

    with pytest.raises(RuntimeError, match="was empty"):
        bootstrap.read_text_from_s3("s3://bucket/current.txt")


def test_read_text_from_s3_returns_trimmed_contents(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap, "s3_client", lambda: FakeS3Client(" s3://bucket/pkg-1.2.3-py3-none-any.whl \n"))

    assert bootstrap.read_text_from_s3("s3://bucket/current.txt") == "s3://bucket/pkg-1.2.3-py3-none-any.whl"


def test_wheel_metadata_helpers() -> None:
    wheel_uri = "s3://bucket/releases/my_package_name-1.2.3-py3-none-any.whl"

    assert bootstrap.wheel_metadata_from_uri(wheel_uri) == ("my-package-name", "1.2.3")
    assert bootstrap.inferred_distribution_from_wheel(wheel_uri) == "my-package-name"
    assert bootstrap.inferred_version_from_wheel(wheel_uri) == "1.2.3"
    assert bootstrap.wheel_metadata_from_uri("s3://bucket/releases/not-a-wheel.txt") == (None, None)


def test_ensure_package_installed_uses_cached_marker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target_dir = tmp_path / "external"
    target_dir.mkdir()
    wheel_uri = "s3://bucket/releases/pkg-1.2.3-py3-none-any.whl"
    bootstrap.marker_path(target_dir).write_text(f"{wheel_uri}\n", encoding="utf-8")

    logged: list[tuple[str, str, Path, str]] = []

    monkeypatch.setattr(bootstrap, "install_dir", lambda: target_dir)
    monkeypatch.setattr(bootstrap, "configured_pointer_uri", lambda: "s3://bucket/current.txt")
    monkeypatch.setattr(bootstrap, "configured_module", lambda: "project.definitions")
    monkeypatch.setattr(bootstrap, "read_text_from_s3", lambda _: wheel_uri)
    monkeypatch.setattr(bootstrap.site, "addsitedir", lambda _: None)
    monkeypatch.setattr(bootstrap.importlib, "invalidate_caches", lambda: None)
    monkeypatch.setattr(bootstrap, "download_wheel", lambda *_: pytest.fail("download should not run"))
    monkeypatch.setattr(bootstrap, "install_wheel", lambda *_: pytest.fail("install should not run"))
    monkeypatch.setattr(bootstrap, "log_bootstrap_metadata", lambda *args: logged.append(args))

    assert bootstrap.ensure_package_installed() == target_dir
    assert logged == [
        (
            "s3://bucket/current.txt",
            wheel_uri,
            target_dir / ".artifacts" / "pkg-1.2.3-py3-none-any.whl",
            "project.definitions",
        )
    ]


def test_ensure_package_installed_downloads_and_installs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target_dir = tmp_path / "external"
    target_dir.mkdir()
    downloaded: list[tuple[str, Path]] = []
    installed: list[tuple[Path, Path]] = []
    logged: list[tuple[str, str, Path, str]] = []
    wheel_uri = "s3://bucket/releases/pkg-1.2.3-py3-none-any.whl"
    wheel_path = target_dir / ".artifacts" / "pkg-1.2.3-py3-none-any.whl"

    monkeypatch.setattr(bootstrap, "install_dir", lambda: target_dir)
    monkeypatch.setattr(bootstrap, "configured_pointer_uri", lambda: "s3://bucket/current.txt")
    monkeypatch.setattr(bootstrap, "configured_module", lambda: "project.definitions")
    monkeypatch.setattr(bootstrap, "read_text_from_s3", lambda _: wheel_uri)
    monkeypatch.setattr(bootstrap.site, "addsitedir", lambda _: None)
    monkeypatch.setattr(bootstrap.importlib, "invalidate_caches", lambda: None)
    monkeypatch.setattr(
        bootstrap,
        "download_wheel",
        lambda uri, destination: downloaded.append((uri, destination)) or wheel_path,
    )
    monkeypatch.setattr(
        bootstrap,
        "install_wheel",
        lambda source, destination: installed.append((source, destination)),
    )
    monkeypatch.setattr(bootstrap, "log_bootstrap_metadata", lambda *args: logged.append(args))

    assert bootstrap.ensure_package_installed() == target_dir
    assert downloaded == [(wheel_uri, target_dir / ".artifacts")]
    assert installed == [(wheel_path, target_dir)]
    assert bootstrap.marker_path(target_dir).read_text(encoding="utf-8") == f"{wheel_uri}\n"
    assert logged == [("s3://bucket/current.txt", wheel_uri, wheel_path, "project.definitions")]


def test_s3_client_uses_configured_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[tuple[str, str]] = []

    monkeypatch.setenv("AWS_ENDPOINT_URL", "https://s3.example.test")
    monkeypatch.setattr(
        bootstrap.boto3,
        "client",
        lambda service_name, endpoint_url: captured.append((service_name, endpoint_url)) or object(),
    )

    bootstrap.s3_client()

    assert captured == [("s3", "https://s3.example.test")]


def test_download_wheel_creates_target_and_downloads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    downloads: list[tuple[str, str, str]] = []
    client = FakeS3Client(downloaded=downloads)

    monkeypatch.setattr(bootstrap, "s3_client", lambda: client)

    wheel_path = bootstrap.download_wheel("s3://bucket/releases/pkg-1.2.3-py3-none-any.whl", tmp_path / "artifacts")

    assert wheel_path == tmp_path / "artifacts" / "pkg-1.2.3-py3-none-any.whl"
    assert wheel_path.read_text(encoding="utf-8") == "wheel"
    assert downloads == [("bucket", "releases/pkg-1.2.3-py3-none-any.whl", str(wheel_path))]


def test_install_wheel_invokes_pip_with_target(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    commands: list[list[str]] = []
    wheel_path = tmp_path / "pkg-1.2.3-py3-none-any.whl"
    target_dir = tmp_path / "installed"
    wheel_path.write_text("wheel", encoding="utf-8")

    monkeypatch.setattr(bootstrap.subprocess, "run", lambda command, check: commands.append(command))

    bootstrap.install_wheel(wheel_path, target_dir)

    assert target_dir.is_dir()
    assert commands == [
        [
            bootstrap.sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--upgrade",
            "--target",
            str(target_dir),
            str(wheel_path),
        ]
    ]


def test_log_bootstrap_metadata_reports_versions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    records: list[tuple[str, str]] = []

    monkeypatch.setattr(bootstrap, "package_version", lambda _: "1.2.3")
    monkeypatch.setattr(bootstrap.LOGGER, "info", lambda message, payload: records.append((message, payload)))

    bootstrap.log_bootstrap_metadata(
        "s3://bucket/current.txt",
        "s3://bucket/releases/my_package_name-1.2.3-py3-none-any.whl",
        tmp_path / "my_package_name-1.2.3-py3-none-any.whl",
        "project.definitions",
    )

    assert records == [
        (
            "Loaded Dagster package release: %s",
            '{"bootstrap_pointer_uri": "s3://bucket/current.txt", "configured_module": "project.definitions", "installed_distribution_version": "1.2.3", "resolved_distribution_name": "my-package-name", "resolved_distribution_version": "1.2.3", "resolved_wheel_filename": "my_package_name-1.2.3-py3-none-any.whl", "resolved_wheel_uri": "s3://bucket/releases/my_package_name-1.2.3-py3-none-any.whl"}',
        )
    ]


def test_log_bootstrap_metadata_handles_missing_distribution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    records: list[str] = []

    monkeypatch.setattr(bootstrap, "package_version", lambda _: (_ for _ in ()).throw(bootstrap.PackageNotFoundError()))
    monkeypatch.setattr(bootstrap.LOGGER, "info", lambda message, payload: records.append(payload))

    bootstrap.log_bootstrap_metadata(
        "s3://bucket/current.txt",
        "s3://bucket/releases/my_package_name-1.2.3-py3-none-any.whl",
        tmp_path / "my_package_name-1.2.3-py3-none-any.whl",
        "project.definitions",
    )

    assert '"installed_distribution_version": null' in records[0]


def test_package_getattr_exposes_defs(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    fake_definitions = types.ModuleType("dagster_user_code.definitions")
    fake_definitions.defs = sentinel
    monkeypatch.setitem(sys.modules, "dagster_user_code.definitions", fake_definitions)

    assert dagster_user_code.__getattr__("defs") is sentinel


def test_package_getattr_rejects_unknown_name() -> None:
    with pytest.raises(AttributeError, match="unknown"):
        dagster_user_code.__getattr__("unknown")
