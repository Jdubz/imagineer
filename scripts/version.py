#!/usr/bin/env python3
"""
Version management script for Imagineer
Handles version bumping, git tagging, and deployment coordination
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_current_version():
    """Get current version from VERSION file"""
    version_file = Path("VERSION")
    if not version_file.exists():
        return "0.0.0"

    with open(version_file, "r") as f:
        return f.read().strip()


def set_version(version):
    """Set version in VERSION file"""
    version_file = Path("VERSION")
    with open(version_file, "w") as f:
        f.write(version)
    print(f"✅ Version set to {version}")


def bump_version(part="patch"):
    """Bump version by part (major, minor, patch)"""
    current = get_current_version()
    parts = current.split(".")

    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {current}")

    major, minor, patch = map(int, parts)

    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid version part: {part}")

    new_version = f"{major}.{minor}.{patch}"
    set_version(new_version)
    return new_version


def update_package_json(version):
    """Update package.json version"""
    package_json = Path("web/package.json")
    if not package_json.exists():
        print("⚠️  web/package.json not found, skipping")
        return

    import json

    with open(package_json, "r") as f:
        data = json.load(f)

    data["version"] = version

    with open(package_json, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"✅ Updated web/package.json to version {version}")


def update_pyproject_toml(version):
    """Update pyproject.toml version"""
    pyproject_toml = Path("pyproject.toml")
    if not pyproject_toml.exists():
        print("⚠️  pyproject.toml not found, skipping")
        return

    content = pyproject_toml.read_text()
    lines = content.split("\n")

    for i, line in enumerate(lines):
        if line.startswith("version = "):
            lines[i] = f'version = "{version}"'
            break
    else:
        # Add version if not found
        lines.insert(0, f'version = "{version}"')

    pyproject_toml.write_text("\n".join(lines))
    print(f"✅ Updated pyproject.toml to version {version}")


def _existing_version_files():
    """Return list of version-managed files that currently exist."""
    candidates = [Path("VERSION"), Path("web/package.json"), Path("pyproject.toml")]
    return [str(path) for path in candidates if path.exists()]


def commit_version_change(version, message=None):
    """Commit updated version files to git."""
    commit_message = message or f"chore: bump version to {version}"
    files_to_stage = _existing_version_files()

    if not files_to_stage:
        print("⚠️  No version-controlled files detected to commit.")
        return False

    try:
        subprocess.run(["git", "add", *files_to_stage], check=True)
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        print(f"✅ Created commit '{commit_message}'")
        return True
    except subprocess.CalledProcessError as error:
        print(f"❌ Git commit failed: {error}")
        return False


def create_git_tag(version, message=None):
    """Create annotated git tag for version."""
    if message is None:
        message = f"Release version {version}"

    try:
        subprocess.run(["git", "tag", "-a", f"v{version}", "-m", message], check=True)
        print(f"✅ Created git tag v{version}")
        return True
    except subprocess.CalledProcessError as error:
        print(f"❌ Git tag failed: {error}")
        return False


def get_build_info():
    """Get build information for deployment"""
    version = get_current_version()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        git_hash = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"❌ Failed to get git hash: {e}")
        git_hash = "unknown"

    return {
        "version": version,
        "timestamp": timestamp,
        "git_hash": git_hash,
        "build_id": f"{version}-{timestamp}-{git_hash}",
    }


def command_current(_):
    print(get_current_version())


def command_bump(args):
    new_version = bump_version(args.part)
    update_package_json(new_version)
    update_pyproject_toml(new_version)
    if args.no_git or commit_version_change(new_version):
        print(f"🎉 Version bumped to {new_version}")
    else:
        sys.exit(1)


def command_set(args):
    if not args.version:
        print("❌ --version required for set command")
        sys.exit(1)
    set_version(args.version)
    update_package_json(args.version)
    update_pyproject_toml(args.version)
    if args.no_git or commit_version_change(args.version):
        print(f"🎉 Version set to {args.version}")
    else:
        sys.exit(1)


def command_tag(args):
    version = get_current_version()
    if args.no_git:
        print(f"ℹ️  Would tag version {version} (--no-git specified)")
        return
    if create_git_tag(version, args.message):
        print(f"🎉 Tagged version {version}")
    else:
        sys.exit(1)


def command_build_info(_):
    info = get_build_info()
    print(f"Version: {info['version']}")
    print(f"Timestamp: {info['timestamp']}")
    print(f"Git Hash: {info['git_hash']}")
    print(f"Build ID: {info['build_id']}")


def main():
    parser = argparse.ArgumentParser(description="Version management for Imagineer")
    parser.add_argument(
        "command",
        choices=["current", "bump", "set", "tag", "build-info"],
        help="Command to execute",
    )
    parser.add_argument(
        "--part",
        choices=["major", "minor", "patch"],
        default="patch",
        help="Version part to bump (for bump command)",
    )
    parser.add_argument("--version", help="Version to set (for set command)")
    parser.add_argument("--message", help="Tag message (for tag command)")
    parser.add_argument("--no-git", action="store_true", help="Skip git operations")

    args = parser.parse_args()

    handlers = {
        "current": command_current,
        "bump": command_bump,
        "set": command_set,
        "tag": command_tag,
        "build-info": command_build_info,
    }

    handlers[args.command](args)


if __name__ == "__main__":
    main()
