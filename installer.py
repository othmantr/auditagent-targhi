#!/usr/bin/env python3
"""Install the local AuditAgent skill and roles without changing host settings.

Python 3.11+. No network, shell commands, dependencies, or credential access.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

VERSION = 1

class InstallError(Exception):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reject_symlinks(path: Path) -> None:
    """Reject existing symlinks at the destination and every ancestor."""
    for candidate in [path, *path.parents]:
        if candidate.is_symlink():
            raise InstallError(f"Refusing symlink destination or ancestor: {candidate}")


def atomic_write(path: Path, data: bytes) -> None:
    reject_symlinks(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".auditagent-install-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def desired_files(source: Path, host: str) -> dict[str, bytes]:
    skill = source / "plugins/auditagent-targhi/skills/auditagent-targhi"
    if not (skill / "SKILL.md").is_file():
        raise InstallError("Source package is incomplete: missing SKILL.md")
    target = ".agents/skills/auditagent-targhi" if host == "codex" else ".claude/skills/auditagent-targhi"
    result = {}
    for path in sorted(skill.rglob("*")):
        if path.is_symlink():
            raise InstallError(f"Refusing symlink in source skill: {path}")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            result[f"{target}/{path.relative_to(skill).as_posix()}"] = path.read_bytes()
    roles = source / ("adapters/codex/agents" if host == "codex" else "plugins/auditagent-targhi/agents")
    extension = ".toml" if host == "codex" else ".md"
    files = sorted(roles.glob(f"*{extension}"))
    if not files:
        raise InstallError(f"Source package is incomplete: no {host} role definitions")
    for path in files:
        if path.is_symlink():
            raise InstallError(f"Refusing symlink source role: {path}")
        relative = f"{'.codex' if host == 'codex' else '.claude'}/agents/{path.name}"
        result[relative] = path.read_bytes()
    return result


def manifest_path(root: Path, host: str) -> Path:
    return root / (".agents" if host == "codex" else ".claude") / "auditagent-targhi.install.json"


def owned_path(relative: str, host: str) -> bool:
    if not isinstance(relative, str) or "\\" in relative:
        return False
    parts = relative.split("/")
    if any(x in {"", ".", ".."} for x in parts):
        return False
    prefix = ".agents/skills/auditagent-targhi/" if host == "codex" else ".claude/skills/auditagent-targhi/"
    role_prefix = ".codex/agents/" if host == "codex" else ".claude/agents/"
    extension = ".toml" if host == "codex" else ".md"
    return relative.startswith(prefix) or (relative.startswith(role_prefix + "auditagent-") and len(parts) == 3 and relative.endswith(extension))


def read_manifest(root: Path, host: str) -> dict[str, str]:
    path = manifest_path(root, host)
    reject_symlinks(path)
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text())
        if value["version"] != VERSION or value["host"] != host or value["root"] != str(root):
            raise ValueError("wrong version, host, or root")
        files = value["files"]
        if not isinstance(files, dict) or not all(owned_path(k, host) and isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v) for k, v in files.items()):
            raise ValueError("invalid file ownership map")
        return files
    except (ValueError, KeyError, TypeError, OSError) as exc:
        raise InstallError(f"Invalid install manifest {path}: {exc}") from exc


def preflight(root: Path, host: str, desired: dict[str, bytes], uninstall: bool) -> dict:
    reject_symlinks(root)
    previous = read_manifest(root, host)
    if uninstall:
        desired = {}
    for relative in set(previous) | set(desired):
        path = root / relative
        reject_symlinks(path)
        if path.exists():
            if not path.is_file():
                raise InstallError(f"Expected a file, found another object: {path}")
            current_hash = digest(path.read_bytes())
            if relative not in previous:
                raise InstallError(f"Unowned file already exists; refusing to replace: {path}")
            if current_hash != previous[relative]:
                raise InstallError(f"Installed file was locally modified; preserve it before updating/removing: {path}")
    return {"host": host, "previous": previous, "desired": desired}


@contextmanager
def installation_lock(root: Path):
    path = root / ".auditagent-targhi-install.lock"
    reject_symlinks(path)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise InstallError(f"Install lock exists: {path}. Check for another installer before removing a stale lock.") from exc
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def install(source: Path, root: Path, hosts: list[str], *, dry_run=False, uninstall=False) -> dict:
    root = Path(os.path.abspath(root))
    reject_symlinks(root)
    if not root.is_dir():
        raise InstallError(f"Destination root must already be a directory: {root}")
    plans = [preflight(root, host, {} if uninstall else desired_files(source, host), uninstall) for host in hosts]
    def describe(current_plans):
        changes = []
        for plan in current_plans:
            old, new = plan["previous"], plan["desired"]
            changes.extend({"host": plan["host"], "action": "remove", "path": key} for key in sorted(set(old) - set(new)))
            changes.extend({"host": plan["host"], "action": "write" if old.get(key) != digest(value) or not (root / key).exists() else "unchanged", "path": key} for key, value in sorted(new.items()))
        return changes
    changes = describe(plans)
    if dry_run:
        return {"dry_run": True, "root": str(root), "changes": changes}
    backups: dict[Path, bytes | None] = {}
    with installation_lock(root):
        # Recheck under the lock so cooperating installer instances cannot race.
        plans = [preflight(root, plan["host"], plan["desired"], uninstall) for plan in plans]
        changes = describe(plans)
        try:
            for plan in plans:
                old, new = plan["previous"], plan["desired"]
                touched = set(old) | set(new)
                for relative in sorted(touched):
                    path = root / relative
                    backups[path] = path.read_bytes() if path.exists() else None
                    if relative in new:
                        if not path.exists() or digest(path.read_bytes()) != digest(new[relative]):
                            atomic_write(path, new[relative])
                    else:
                        path.unlink(missing_ok=True)
                meta = manifest_path(root, plan["host"])
                backups[meta] = meta.read_bytes() if meta.exists() else None
                if uninstall:
                    meta.unlink(missing_ok=True)
                else:
                    payload = {"version": VERSION, "host": plan["host"], "root": str(root), "files": {key: digest(data) for key, data in sorted(new.items())}}
                    atomic_write(meta, (json.dumps(payload, indent=2) + "\n").encode())
        except Exception:
            # Best effort rollback. The installer is not a hostile-filesystem sandbox.
            for path, original in reversed(list(backups.items())):
                if original is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_write(path, original)
            raise
        if uninstall:
            # Remove only empty directories under the skill, leaving unrelated files alone.
            for host in hosts:
                skill = root / (".agents" if host == "codex" else ".claude") / "skills/auditagent-targhi"
                if skill.is_dir():
                    for directory in sorted((p for p in skill.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
                        try:
                            directory.rmdir()
                        except OSError:
                            pass
                    try:
                        skill.rmdir()
                    except OSError:
                        pass
    return {"dry_run": False, "root": str(root), "changes": changes, "uninstalled": uninstall}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=["codex", "claude", "both"], required=True)
    parser.add_argument("--scope", choices=["user", "project"], default="user")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = install(Path(__file__).absolute().parent, Path.home() if args.scope == "user" else args.project, ["codex", "claude"] if args.host == "both" else [args.host], dry_run=args.dry_run, uninstall=args.uninstall)
        print(json.dumps(result, indent=2))
    except (InstallError, OSError) as exc:
        print(f"Install failed: {exc}", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
