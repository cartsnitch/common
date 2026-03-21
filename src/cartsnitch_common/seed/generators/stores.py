"""Generate Store and StoreLocation seed data."""

import uuid
from datetime import UTC, datetime

from cartsnitch_common.constants import StoreSlug
from cartsnitch_common.seed.config import NUM_LOCATIONS_PER_STORE

# Fixed store definitions
_STORE_DEFS: list[dict] = [
    {
        "name": "Meijer",
        "slug": StoreSlug.MEIJER,
        "logo_url": "https://www.meijer.com/favicon.ico",
        "website_url": "https://www.meijer.com",
    },
    {
        "name": "Kroger",
        "slug": StoreSlug.KROGER,
        "logo_url": "https://www.kroger.com/favicon.ico",
        "website_url": "https://www.kroger.com",
    },
    {
        "name": "Target",
        "slug": StoreSlug.TARGET,
        "logo_url": "https://www.target.com/favicon.ico",
        "website_url": "https://www.target.com",
    },
]

# SE Michigan locations per store (5 each = 15 total)
_LOCATION_DEFS: dict[StoreSlug, list[dict]] = {
    StoreSlug.MEIJER: [
        {
            "address": "3145 Ann Arbor-Saline Rd",
            "city": "Ann Arbor",
            "state": "MI",
            "zip": "48103",
            "lat": 42.2434,
            "lng": -83.8102,
        },
        {
            "address": "700 W Ellsworth Rd",
            "city": "Ann Arbor",
            "state": "MI",
            "zip": "48108",
            "lat": 42.2318,
            "lng": -83.7581,
        },
        {
            "address": "5100 Oakman Blvd",
            "city": "Dearborn",
            "state": "MI",
            "zip": "48126",
            "lat": 42.3223,
            "lng": -83.1952,
        },
        {
            "address": "15555 Northline Rd",
            "city": "Southgate",
            "state": "MI",
            "zip": "48195",
            "lat": 42.2089,
            "lng": -83.1953,
        },
        {
            "address": "2855 Washtenaw Ave",
            "city": "Ypsilanti",
            "state": "MI",
            "zip": "48197",
            "lat": 42.2461,
            "lng": -83.6388,
        },
    ],
    StoreSlug.KROGER: [
        {
            "address": "2010 W Stadium Blvd",
            "city": "Ann Arbor",
            "state": "MI",
            "zip": "48103",
            "lat": 42.2706,
            "lng": -83.7807,
        },
        {
            "address": "1100 S Main St",
            "city": "Ann Arbor",
            "state": "MI",
            "zip": "48104",
            "lat": 42.2555,
            "lng": -83.7469,
        },
        {
            "address": "23650 Michigan Ave",
            "city": "Dearborn",
            "state": "MI",
            "zip": "48124",
            "lat": 42.3221,
            "lng": -83.2135,
        },
        {
            "address": "14000 Michigan Ave",
            "city": "Dearborn",
            "state": "MI",
            "zip": "48126",
            "lat": 42.3281,
            "lng": -83.1789,
        },
        {
            "address": "3965 Packard St",
            "city": "Ann Arbor",
            "state": "MI",
            "zip": "48108",
            "lat": 42.2298,
            "lng": -83.7196,
        },
    ],
    StoreSlug.TARGET: [
        {
            "address": "3165 Ann Arbor-Saline Rd",
            "city": "Ann Arbor",
            "state": "MI",
            "zip": "48103",
            "lat": 42.2431,
            "lng": -83.8097,
        },
        {
            "address": "4001 Carpenter Rd",
            "city": "Ypsilanti",
            "state": "MI",
            "zip": "48197",
            "lat": 42.2373,
            "lng": -83.6617,
        },
        {
            "address": "16000 Ford Rd",
            "city": "Dearborn",
            "state": "MI",
            "zip": "48126",
            "lat": 42.3312,
            "lng": -83.2098,
        },
        {
            "address": "17300 Eureka Rd",
            "city": "Southgate",
            "state": "MI",
            "zip": "48195",
            "lat": 42.2001,
            "lng": -83.2014,
        },
        {
            "address": "2400 E Stadium Blvd",
            "city": "Ann Arbor",
            "state": "MI",
            "zip": "48104",
            "lat": 42.2624,
            "lng": -83.7102,
        },
    ],
}


def generate_stores() -> list[dict]:
    """Return 3 fixed store records."""
    now = datetime.now(tz=UTC)
    stores = []
    for defn in _STORE_DEFS:
        stores.append(
            {
                "id": uuid.uuid4(),
                "name": defn["name"],
                "slug": defn["slug"],
                "logo_url": defn["logo_url"],
                "website_url": defn["website_url"],
                "created_at": now,
                "updated_at": now,
            }
        )
    return stores


def generate_store_locations(stores: list[dict]) -> list[dict]:
    """Return 5 locations per store (15 total)."""
    now = datetime.now(tz=UTC)
    slug_to_id = {s["slug"]: s["id"] for s in stores}
    locations = []
    for slug, loc_defs in _LOCATION_DEFS.items():
        store_id = slug_to_id[slug]
        for loc in loc_defs[:NUM_LOCATIONS_PER_STORE]:
            locations.append(
                {
                    "id": uuid.uuid4(),
                    "store_id": store_id,
                    "address": loc["address"],
                    "city": loc["city"],
                    "state": loc["state"],
                    "zip": loc["zip"],
                    "lat": loc["lat"],
                    "lng": loc["lng"],
                    "created_at": now,
                    "updated_at": now,
                }
            )
    return locations
