"""Build and validate reproducible AWS Lambda ZIP artifacts."""

from __future__ import annotations

import argparse
import hashlib
import stat
import zipfile
from pathlib import Path


def create_deterministic_zip(package_dir: Path, output_path: Path) -> str:
    package_dir = package_dir.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(
        path
        for path in package_dir.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    with zipfile.ZipFile(
        output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in files:
            relative = path.relative_to(package_dir).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    return hashlib.sha256(output_path.read_bytes()).hexdigest()


def validate_lambda_archive(
    archive_path: Path, *, required_modules: tuple[str, ...] = ("pydantic",)
) -> str:
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
    required_paths = {"src/handlers/order_ingest.py", "src/handlers/order_worker.py"}
    missing_paths = sorted(required_paths - names)
    missing_modules = sorted(
        module
        for module in required_modules
        if f"{module}/__init__.py" not in names and f"{module}.py" not in names
    )
    missing = [*missing_paths, *missing_modules]
    if missing:
        raise ValueError(f"Lambda archive is missing required content: {', '.join(missing)}")
    return digest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a deterministic Lambda ZIP")
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--required-module", action="append", default=["pydantic"])
    arguments = parser.parse_args()
    artifact_digest = create_deterministic_zip(arguments.package_dir, arguments.output)
    validate_lambda_archive(arguments.output, required_modules=tuple(arguments.required_module))
    print(f"{arguments.output} sha256:{artifact_digest}")
