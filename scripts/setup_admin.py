#!/usr/bin/env python3
"""
Setup script to create admin users for Imagineer
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.auth import ROLE_ADMIN, load_users, save_users  # noqa: E402


def setup_admin(email):
    """Set up an admin user"""
    users = load_users()

    if email not in users:
        users[email] = {}

    users[email]["role"] = ROLE_ADMIN

    save_users(users)
    print(f"✅ Set {email} as admin user")

    return users


def list_users():
    """List all users and their roles"""
    users = load_users()

    if not users:
        print("No users found")
        return

    print("\nCurrent users:")
    for email, data in users.items():
        # Skip metadata fields that are strings
        if isinstance(data, str):
            continue
        role = data.get("role", "public")
        print(f"  {email}: {role}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python setup_admin.py <email>     # Set user as admin")
        print("  python setup_admin.py list        # List all users")
        return

    command = sys.argv[1]

    if command == "list":
        list_users()
    else:
        email = command
        setup_admin(email)
        list_users()


if __name__ == "__main__":
    main()
