"""One-off CLI to create an admin account. Admins are never self-registered
through the public API (see app/schemas/auth.py), so this is the only way to
create one.

Usage: python -m scripts.create_admin <email> <password> <display_name>
"""

import sys

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import AdminProfile, User, UserRole


def main() -> None:
    if len(sys.argv) != 4:
        print("Usage: python -m scripts.create_admin <email> <password> <display_name>")
        raise SystemExit(1)

    email, password, display_name = sys.argv[1], sys.argv[2], sys.argv[3]

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            print(f"A user with email {email} already exists.")
            raise SystemExit(1)

        user = User(
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.flush()
        db.add(AdminProfile(user_id=user.id, display_name=display_name))
        db.commit()
        print(f"Created admin account {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
