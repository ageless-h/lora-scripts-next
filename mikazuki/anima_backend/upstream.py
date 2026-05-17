from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path


_SUBMODULE_HINT = (
    "Anima backend requires the pinned sd-scripts submodule at {path}.\n"
    "Run `git submodule update --init --recursive` from the repo root to "
    "initialize it.\n"
    "To intentionally use a different commit, set ANIMA_ALLOW_COMMIT_DRIFT=1 "
    "to downgrade the version check to a warning."
)


def load_toml_file(path: Path) -> dict:
    try:
        import tomllib

        with path.open("rb") as config_file:
            return tomllib.load(config_file)
    except ModuleNotFoundError:
        import toml

        return toml.load(path)


def resolve_upstream_path(root: Path, config_path: Path | None = None) -> Path:
    config_path = config_path or root / "config" / "anima_backend.toml"
    data = load_toml_file(config_path)

    upstream_path = Path(data["backend"]["upstream_path"])
    if not upstream_path.is_absolute():
        upstream_path = root / upstream_path
    return upstream_path.resolve()


def pinned_commit(root: Path, config_path: Path | None = None) -> str:
    config_path = config_path or root / "config" / "anima_backend.toml"
    data = load_toml_file(config_path)
    return str(data["backend"]["pinned_commit"])


def _is_initialized_git_checkout(upstream_path: Path) -> bool:
    """Return True if upstream_path is itself a git work tree.

    A submodule that has not been initialized leaves an empty directory (or no
    directory at all) under ``vendor/sd-scripts``. Running ``git rev-parse`` in
    that location would walk up and resolve to the superproject, which silently
    produces a HEAD that has nothing to do with sd-scripts. Guard against that
    by verifying both ``.git`` exists in the directory and that git itself
    reports the directory as the top-level of its work tree.
    """

    if not upstream_path.exists() or not (upstream_path / ".git").exists():
        return False
    try:
        result = subprocess.run(
            ["git", "-C", str(upstream_path), "rev-parse", "--show-toplevel"],
            text=True,
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    try:
        toplevel = Path(result.stdout.strip()).resolve()
    except OSError:
        return False
    return toplevel == upstream_path.resolve()


def current_upstream_commit(upstream_path: Path) -> str:
    if not _is_initialized_git_checkout(upstream_path):
        raise RuntimeError(_SUBMODULE_HINT.format(path=upstream_path))
    result = subprocess.run(
        ["git", "-C", str(upstream_path), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def _drift_allowed() -> bool:
    return os.environ.get("ANIMA_ALLOW_COMMIT_DRIFT", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def verify_pinned_commit(root: Path, config_path: Path | None = None) -> str:
    upstream_path = resolve_upstream_path(root, config_path)
    expected = pinned_commit(root, config_path)

    if not _is_initialized_git_checkout(upstream_path):
        raise RuntimeError(_SUBMODULE_HINT.format(path=upstream_path))

    actual = current_upstream_commit(upstream_path)
    if actual != expected:
        message = (
            "Pinned sd-scripts commit mismatch: "
            f"config expects {expected}, but {upstream_path} is at {actual}"
        )
        if _drift_allowed():
            print(
                f"[Anima backend] WARNING: {message} "
                "(ANIMA_ALLOW_COMMIT_DRIFT is set, continuing anyway)",
                file=sys.stderr,
            )
            return actual
        raise RuntimeError(
            message
            + "\nSet ANIMA_ALLOW_COMMIT_DRIFT=1 to bypass this check."
        )
    return actual


def upstream_entrypoint(upstream_path: Path, entrypoint: str) -> Path:
    script = upstream_path / entrypoint
    if not script.exists():
        raise FileNotFoundError(f"Upstream Anima trainer not found: {script}")
    return script


def prefer_upstream_imports(upstream_path: Path) -> None:
    upstream = str(upstream_path.resolve())
    if upstream in sys.path:
        sys.path.remove(upstream)
    sys.path.insert(0, upstream)
