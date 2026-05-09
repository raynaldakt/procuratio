from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from sqlalchemy import select

# Ensure imports work when running from /app in container or from repo root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.customer_profile import CustomerProfile
from app.models.employee_profile import EmployeeProfile
from app.models.user import User
from app.services.appointments import ensure_appointments_schema
from app.services.customer import ensure_customer_schema, get_or_create_profile


@dataclass(frozen=True)
class DemoAccount:
    email: str
    password: str
    full_name: str
    role: str


DEMO_ACCOUNTS: tuple[DemoAccount, ...] = (
    DemoAccount("admin@procuratio.demo", "Admin123!", "Demo Admin", "admin"),
    DemoAccount("manager@procuratio.demo", "Manager123!", "Demo Manager", "manager"),
    DemoAccount("staff@procuratio.demo", "Staff123!", "Demo Staff", "staff"),
    DemoAccount("customer@procuratio.demo", "Customer123!", "Demo Customer", "customer"),
)


def upsert_user(db, account: DemoAccount) -> User:
    user = db.scalar(select(User).where(User.email == account.email.lower()))
    if user is None:
        user = User(
            email=account.email.lower(),
            hashed_password=hash_password(account.password),
            full_name=account.full_name,
            role=account.role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    user.full_name = account.full_name
    user.role = account.role
    user.is_active = True
    user.hashed_password = hash_password(account.password)
    db.commit()
    db.refresh(user)
    return user


def ensure_employee_profile(db, user_id: int) -> None:
    profile = db.get(EmployeeProfile, user_id)
    if profile is None:
        profile = EmployeeProfile(
            user_id=user_id,
            is_bookable=True,
            workday_start_minute=9 * 60,
            workday_end_minute=19 * 60,
            slot_step_minutes=15,
        )
        db.add(profile)
    else:
        profile.is_bookable = True

    db.commit()


def ensure_customer_profile(db, user_id: int) -> None:
    profile = get_or_create_profile(db, user_id)
    if profile.marketing_email_opt_in is False:
        profile.marketing_email_opt_in = True
    db.commit()


def main() -> None:
    ensure_customer_schema()
    ensure_appointments_schema()

    print("Seeding demo accounts...")
    with SessionLocal() as db:
        created_or_updated: list[tuple[str, str]] = []
        for account in DEMO_ACCOUNTS:
            user = upsert_user(db, account)

            if account.role in {"admin", "manager", "staff"}:
                ensure_employee_profile(db, user.id)

            if account.role == "customer":
                ensure_customer_profile(db, user.id)

            created_or_updated.append((account.role, account.email))

    print("Done. Accounts ready:")
    for role, email in created_or_updated:
        print(f"- {role}: {email}")


if __name__ == "__main__":
    main()
