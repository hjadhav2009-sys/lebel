import argparse
import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Role,User

ROLES=("Admin","QC","Packing","Print Operator")


def main():
    parser=argparse.ArgumentParser(description="Create the first MMS local Admin without a default credential.")
    parser.add_argument("--email",required=True);parser.add_argument("--name",required=True);args=parser.parse_args()
    password=getpass.getpass("New Admin password (12+ characters): ")
    if len(password)<12:raise SystemExit("Password must contain at least 12 characters.")
    confirmation=getpass.getpass("Confirm password: ")
    if password!=confirmation:raise SystemExit("Passwords do not match.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email==args.email.casefold())):raise SystemExit("User already exists.")
        existing={role.name:role for role in db.scalars(select(Role).where(Role.name.in_(ROLES))).all()}
        for name in ROLES:
            if name not in existing:existing[name]=Role(name=name);db.add(existing[name])
        db.flush();user=User(email=args.email.casefold(),display_name=args.name,password_hash=hash_password(password),is_active=True,roles=[existing["Admin"]]);db.add(user);db.commit()
    print("Bootstrap Admin created.")


if __name__=="__main__":main()
