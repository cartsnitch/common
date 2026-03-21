"""Generate User and UserStoreAccount seed data."""

import random
import uuid
from datetime import UTC, datetime, timedelta

from faker import Faker

from cartsnitch_common.constants import AccountStatus
from cartsnitch_common.seed.config import (
    NUM_ACTIVE_USERS,
    NUM_USER_STORE_ACCOUNTS,
    NUM_USERS,
    SEED_END_DATE,
)


def generate_users(fake: Faker) -> list[dict]:
    """Return NUM_USERS user records. First NUM_ACTIVE_USERS are active."""
    now = datetime.now(tz=UTC)
    users = []
    for i in range(NUM_USERS):
        created_at = now - timedelta(days=random.randint(30, 365))
        users.append(
            {
                "id": uuid.uuid4(),
                "email": fake.unique.email(),
                "hashed_password": fake.sha256(),
                "display_name": fake.name() if random.random() > 0.2 else None,
                "created_at": created_at,
                "updated_at": created_at,
                "_active": i < NUM_ACTIVE_USERS,
            }
        )
    return users


def generate_user_store_accounts(
    users: list[dict],
    stores: list[dict],
) -> list[dict]:
    """Return ~NUM_USER_STORE_ACCOUNTS user-store account links.

    Active users get accounts at multiple stores; inactive users may have none.
    """
    now = datetime.now(tz=UTC)
    accounts = []
    seen: set[tuple] = set()

    active_users = [u for u in users if u["_active"]]
    inactive_users = [u for u in users if not u["_active"]]

    # Active users: each gets 1-3 store accounts
    for user in active_users:
        num_accounts = random.randint(1, 3)
        selected_stores = random.sample(stores, min(num_accounts, len(stores)))
        for store in selected_stores:
            key = (user["id"], store["id"])
            if key in seen:
                continue
            seen.add(key)
            last_sync = datetime(
                SEED_END_DATE.year,
                SEED_END_DATE.month,
                SEED_END_DATE.day,
                tzinfo=UTC,
            ) - timedelta(days=random.randint(0, 14))
            accounts.append(
                {
                    "id": uuid.uuid4(),
                    "user_id": user["id"],
                    "store_id": store["id"],
                    "session_data": {"token": "SEED_FAKE_TOKEN", "expires": "2026-12-31"},
                    "session_expires_at": now + timedelta(days=random.randint(1, 90)),
                    "last_sync_at": last_sync,
                    "status": AccountStatus.ACTIVE,
                    "created_at": user["created_at"],
                    "updated_at": user["updated_at"],
                }
            )

    # Fill remaining slots from inactive users
    remaining = NUM_USER_STORE_ACCOUNTS - len(accounts)
    for user in random.sample(inactive_users, min(remaining, len(inactive_users))):
        store = random.choice(stores)
        key = (user["id"], store["id"])
        if key in seen:
            continue
        seen.add(key)
        status = random.choice([AccountStatus.EXPIRED, AccountStatus.ERROR, AccountStatus.ACTIVE])
        accounts.append(
            {
                "id": uuid.uuid4(),
                "user_id": user["id"],
                "store_id": store["id"],
                "session_data": None,
                "session_expires_at": None,
                "last_sync_at": None,
                "status": status,
                "created_at": user["created_at"],
                "updated_at": user["updated_at"],
            }
        )

    return accounts[: NUM_USER_STORE_ACCOUNTS + len(active_users) * 3]
