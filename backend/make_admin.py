"""Give or take away admin rights.

    python make_admin.py you@example.com           # make admin
    python make_admin.py you@example.com --remove  # back to a regular user
"""
import sys

from models import SessionLocal, User, init_db


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        sys.exit(1)

    email = args[0].strip()
    role = "user" if "--remove" in sys.argv else "admin"

    init_db()   # make sure the role column exists
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"No user with email {email}. Register in the app first.")
            sys.exit(1)
        user.role = role
        if role == "admin":
            user.is_banned = False
        db.commit()
        print(f"{user.username} <{user.email}> is now: {role}. Log out and in again to see the change.")


if __name__ == "__main__":
    main()
