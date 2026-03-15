# CartSnitch Common Library

## Project Context

CartSnitch is a self-hosted grocery price intelligence platform built as a polyrepo microservices architecture. This repo (`cartsnitch/common`) is the shared Python library that all CartSnitch services depend on.

**GitHub org:** github.com/cartsnitch
**Domain:** cartsnitch.com

### CartSnitch Services

| Repo | Service | Purpose |
|------|---------|---------|
| `cartsnitch/common` | — | Shared models, schemas, utilities (this repo) |
| `cartsnitch/receiptwitness` | ReceiptWitness | Purchase data ingestion via retailer scrapers |
| `cartsnitch/api` | API Gateway | Frontend-facing REST API |
| `cartsnitch/cartsnitch` | Frontend | React PWA (mobile-first) |
| `cartsnitch/stickershock` | StickerShock | Price increase detection & CPI comparison |
| `cartsnitch/shrinkray` | ShrinkRay | Shrinkflation monitoring |
| `cartsnitch/clipartist` | ClipArtist | Coupon/deal watching & shopping optimization |
| `cartsnitch/infra` | — | K8s manifests, Flux kustomizations |

### Architecture Decisions

- **Polyrepo:** Each service has its own repo, Dockerfile, CI/CD pipeline.
- **Shared DB:** One PostgreSQL cluster (CNPG on K8s, docker-compose locally). Each service owns its tables but shares the database. Services access other services' data via REST API, not direct cross-service DB queries.
- **Inter-service comms:** REST (synchronous) + Redis pub/sub (async events).
- **Target scale:** 500–1,000 users initially.
- **Target retailers (MVP):** Meijer (mPerks), Kroger, Target (Circle) in Southeast Michigan.

## What This Repo Contains

This is a Python package (`cartsnitch-common`) that provides:

1. **SQLAlchemy ORM models** — the canonical database schema shared across services
2. **Pydantic schemas** — request/response models for inter-service API contracts
3. **Database utilities** — engine/session factory, connection management
4. **Configuration** — shared settings via pydantic-settings (DB URL, Redis URL, etc.)
5. **Event definitions** — Redis pub/sub event types and payloads
6. **Constants** — store slugs, category enums, etc.

## Tech Stack

- Python 3.12+
- SQLAlchemy 2.0 (async support)
- Alembic (migrations live in this repo since it owns the schema)
- Pydantic v2
- pydantic-settings (env-based configuration)
- Redis (py-redis for pub/sub event definitions)

## Database Schema

All migrations are managed from this repo via Alembic. Services depend on `cartsnitch-common` to get the models.

### Core Tables

```
stores
  id (PK), name, slug (meijer|kroger|target), logo_url, website_url, created_at

store_locations
  id (PK), store_id (FK), address, city, state, zip, lat, lng

users
  id (PK), email, hashed_password, display_name, created_at, updated_at

user_store_accounts
  id (PK), user_id (FK), store_id (FK), session_data (encrypted JSONB), session_expires_at, last_sync_at, status (active|expired|error)

purchases
  id (PK), user_id (FK), store_id (FK), store_location_id (FK), receipt_id (unique per store), purchase_date, total, subtotal, tax, savings_total, source_url, raw_data (JSONB), ingested_at

purchase_items
  id (PK), purchase_id (FK), product_name_raw, upc, quantity, unit_price, extended_price, regular_price, sale_price, coupon_discount, loyalty_discount, category_raw, normalized_product_id (FK, nullable)

normalized_products
  id (PK), canonical_name, category, subcategory, brand, size, size_unit, upc_variants (JSONB), created_at, updated_at

price_history
  id (PK), normalized_product_id (FK), store_id (FK), observed_date, regular_price, sale_price, loyalty_price, coupon_price, source (receipt|catalog|weekly_ad), purchase_item_id (FK, nullable)

coupons
  id (PK), store_id (FK), normalized_product_id (FK, nullable), title, description, discount_type (percent|fixed|bogo|buy_x_get_y), discount_value, min_purchase, valid_from, valid_to, requires_clip, coupon_code, source_url, scraped_at

shrinkflation_events
  id (PK), normalized_product_id (FK), detected_date, old_size, new_size, old_unit, new_unit, price_at_old_size, price_at_new_size, confidence, notes
```

## Repo Structure

```
cartsnitch-common/
├── CLAUDE.md
├── README.md
├── pyproject.toml              # Package definition, installable via pip
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── src/
│   └── cartsnitch_common/
│       ├── __init__.py
│       ├── config.py           # Shared settings (DB_URL, REDIS_URL, etc.)
│       ├── database.py         # Engine, session factory, async support
│       ├── models/
│       │   ├── __init__.py     # Re-exports all models
│       │   ├── base.py         # DeclarativeBase, common mixins (timestamps, etc.)
│       │   ├── store.py        # Store, StoreLocation
│       │   ├── user.py         # User, UserStoreAccount
│       │   ├── purchase.py     # Purchase, PurchaseItem
│       │   ├── product.py      # NormalizedProduct
│       │   ├── price.py        # PriceHistory
│       │   ├── coupon.py       # Coupon
│       │   └── shrinkflation.py # ShrinkflationEvent
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── purchase.py     # Pydantic request/response schemas
│       │   ├── product.py
│       │   ├── price.py
│       │   ├── coupon.py
│       │   └── events.py       # Redis pub/sub event payloads
│       ├── events.py           # Event bus helpers (publish/subscribe)
│       └── constants.py        # Store slugs, enums
└── tests/
    ├── conftest.py
    ├── test_models.py
    └── test_schemas.py
```

## Packaging

This package is published as `cartsnitch-common` and installed by other services via:

```
# In each service's pyproject.toml
dependencies = [
    "cartsnitch-common @ git+https://github.com/cartsnitch/common.git@main",
]
```

Or if using a private PyPI registry, publish there. For local dev, install in editable mode:

```bash
pip install -e /path/to/common
```

## Development Workflow

- **Never push directly to main.** Always create feature branches and open PRs.
- Branch naming: `feature/<description>` or `fix/<description>`
- Use conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`
- Alembic migrations must be reviewed carefully — they affect all services.
- Bump the version in `pyproject.toml` when changing schemas or models so downstream services can pin versions.
- Run `alembic upgrade head` in local dev after pulling changes.

## Event Bus (Redis Pub/Sub)

Events are the primary async communication mechanism between services. Event types are defined in this repo so all services share the same contract.

### Event Channels

- `cartsnitch.receipts.ingested` — ReceiptWitness publishes when new receipt data is saved
- `cartsnitch.prices.updated` — Published when new price data points are recorded
- `cartsnitch.products.normalized` — Published when product normalization resolves a match
- `cartsnitch.coupons.updated` — ClipArtist publishes when coupon data refreshes
- `cartsnitch.alerts.price_increase` — StickerShock publishes when a significant price increase is detected
- `cartsnitch.alerts.shrinkflation` — ShrinkRay publishes when shrinkflation is detected

### Event Payload Structure

```json
{
  "event_type": "cartsnitch.receipts.ingested",
  "timestamp": "2026-03-15T12:00:00Z",
  "service": "receiptwitness",
  "payload": { ... }
}
```

## Important Notes

- This is the schema owner. All Alembic migrations live here. No other service runs its own migrations.
- When adding new models or changing existing ones, always create a migration and bump the package version.
- Pydantic schemas in `schemas/` define the API contracts between services. These are the source of truth for inter-service communication.
- The `database.py` module should support both sync and async sessions since different services may use different patterns.
