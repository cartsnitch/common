"""Generate NormalizedProduct seed data."""

import random
import uuid
from datetime import UTC, datetime

from faker import Faker

from cartsnitch_common.constants import ProductCategory, SizeUnit
from cartsnitch_common.seed.config import NUM_PRODUCTS

# Product templates per category: (category, brands, names, sizes, default_unit)
_PRODUCT_TEMPLATES: list[tuple[ProductCategory, list[str], list[str], list[str], SizeUnit]] = [
    (
        ProductCategory.PRODUCE,
        ["Organic Valley", "Earthbound Farm", "Local Farm", "Fresh Farms"],
        [
            "Bananas",
            "Apples",
            "Baby Carrots",
            "Spinach",
            "Broccoli",
            "Strawberries",
            "Blueberries",
            "Grapes",
            "Tomatoes",
            "Lettuce",
        ],
        ["1 lb", "2 lb", "16 oz", "12 oz", "5 oz", "6 oz", "32 oz"],
        SizeUnit.LB,
    ),
    (
        ProductCategory.DAIRY,
        ["Kraft", "Tillamook", "Great Value", "Land O'Lakes", "Daisy", "Organic Valley"],
        [
            "Whole Milk",
            "2% Milk",
            "Cheddar Cheese",
            "Mozzarella",
            "Greek Yogurt",
            "Butter",
            "Cream Cheese",
            "Sour Cream",
            "Heavy Cream",
            "Cottage Cheese",
        ],
        ["16 oz", "32 oz", "64 oz", "1 gallon", "8 oz", "12 oz", "5 oz"],
        SizeUnit.FL_OZ,
    ),
    (
        ProductCategory.MEAT,
        ["Tyson", "Perdue", "Smithfield", "Oscar Mayer", "Applegate", "Kirkland"],
        [
            "Chicken Breast",
            "Ground Beef",
            "Pork Chops",
            "Bacon",
            "Turkey",
            "Salmon",
            "Tilapia",
            "Sausage",
            "Hot Dogs",
            "Deli Ham",
        ],
        ["1 lb", "2 lb", "3 lb", "12 oz", "16 oz", "24 oz"],
        SizeUnit.LB,
    ),
    (
        ProductCategory.BAKERY,
        ["Nature's Own", "Dave's Killer Bread", "Pepperidge Farm", "Sara Lee", "Arnold"],
        [
            "White Bread",
            "Whole Wheat Bread",
            "Sourdough",
            "Bagels",
            "English Muffins",
            "Croissants",
            "Dinner Rolls",
            "Hamburger Buns",
            "Hot Dog Buns",
            "Muffins",
        ],
        ["20 oz", "24 oz", "6 ct", "8 ct", "12 ct", "16 oz"],
        SizeUnit.OZ,
    ),
    (
        ProductCategory.FROZEN,
        ["Stouffer's", "Amy's", "Birds Eye", "Green Giant", "Totino's", "DiGiorno"],
        [
            "Frozen Pizza",
            "Mac and Cheese",
            "Frozen Burritos",
            "Chicken Nuggets",
            "Fish Sticks",
            "Frozen Vegetables",
            "Ice Cream",
            "Frozen Waffles",
            "Tater Tots",
            "Frozen Lasagna",
        ],
        ["12 oz", "16 oz", "24 oz", "32 oz", "4 ct", "8 ct"],
        SizeUnit.OZ,
    ),
    (
        ProductCategory.PANTRY,
        ["Campbell's", "Hunt's", "Kraft", "Heinz", "Del Monte", "General Mills", "Kellogg's"],
        [
            "Pasta Sauce",
            "Canned Tomatoes",
            "Chicken Noodle Soup",
            "Peanut Butter",
            "Jelly",
            "Olive Oil",
            "Rice",
            "Pasta",
            "Oatmeal",
            "Cereal",
        ],
        ["15 oz", "24 oz", "32 oz", "18 oz", "16 oz", "24 oz", "48 oz", "64 oz"],
        SizeUnit.OZ,
    ),
    (
        ProductCategory.BEVERAGES,
        ["Coca-Cola", "Pepsi", "Tropicana", "Minute Maid", "Gatorade", "LaCroix", "Nestle"],
        [
            "Cola",
            "Diet Cola",
            "Orange Juice",
            "Apple Juice",
            "Sports Drink",
            "Sparkling Water",
            "Iced Coffee",
            "Energy Drink",
            "Lemonade",
            "Green Tea",
        ],
        ["12 fl oz", "20 fl oz", "32 fl oz", "64 fl oz", "2 liter", "6 pk", "12 pk"],
        SizeUnit.FL_OZ,
    ),
    (
        ProductCategory.SNACKS,
        ["Frito-Lay", "Nabisco", "Kellogg's", "Pepperidge Farm", "Clif Bar", "KIND", "Planters"],
        [
            "Potato Chips",
            "Tortilla Chips",
            "Pretzels",
            "Crackers",
            "Granola Bars",
            "Trail Mix",
            "Popcorn",
            "Cookies",
            "Nuts",
            "Fruit Snacks",
        ],
        ["7 oz", "10 oz", "16 oz", "6 ct", "12 ct", "18 ct", "3.5 oz"],
        SizeUnit.OZ,
    ),
    (
        ProductCategory.HOUSEHOLD,
        ["Tide", "Dawn", "Bounty", "Charmin", "Clorox", "Method", "Seventh Generation"],
        [
            "Laundry Detergent",
            "Dish Soap",
            "Paper Towels",
            "Toilet Paper",
            "Bleach",
            "All-Purpose Cleaner",
            "Fabric Softener",
            "Dryer Sheets",
            "Trash Bags",
            "Sponges",
        ],
        ["32 oz", "64 oz", "100 oz", "6 pk", "12 pk", "24 ct", "2 pk"],
        SizeUnit.OZ,
    ),
    (
        ProductCategory.PERSONAL_CARE,
        ["Dove", "Pantene", "Colgate", "Crest", "Gillette", "L'Oreal", "Neutrogena"],
        [
            "Shampoo",
            "Conditioner",
            "Body Wash",
            "Toothpaste",
            "Deodorant",
            "Face Wash",
            "Lotion",
            "Razor",
            "Shaving Cream",
            "Hand Soap",
        ],
        ["12 oz", "24 oz", "32 oz", "3.4 oz", "6 oz", "8 oz", "2 pk"],
        SizeUnit.OZ,
    ),
]


def _generate_upc() -> str:
    """Generate a fake 12-digit UPC."""
    digits = [random.randint(0, 9) for _ in range(11)]
    odd_sum = sum(digits[i] for i in range(0, 11, 2))
    even_sum = sum(digits[i] for i in range(1, 11, 2))
    check = (10 - ((odd_sum * 3 + even_sum) % 10)) % 10
    digits.append(check)
    return "".join(str(d) for d in digits)


def generate_products(fake: Faker) -> list[dict]:
    """Return NUM_PRODUCTS normalized product records."""
    now = datetime.now(tz=UTC)
    products = []
    used_upcs: set[str] = set()

    per_category = NUM_PRODUCTS // len(_PRODUCT_TEMPLATES)
    remainder = NUM_PRODUCTS % len(_PRODUCT_TEMPLATES)

    for i, (category, brands, names, sizes, default_unit) in enumerate(_PRODUCT_TEMPLATES):
        count = per_category + (1 if i < remainder else 0)
        for _ in range(count):
            brand = random.choice(brands)
            product_name = random.choice(names)
            size_str = random.choice(sizes)
            canonical_name = f"{brand} {product_name} {size_str}"

            size_parts = size_str.split(" ", 1)
            size_val = size_parts[0]

            num_upcs = random.randint(1, 3)
            upcs: list[str] = []
            for _ in range(num_upcs):
                upc = _generate_upc()
                attempts = 0
                while upc in used_upcs and attempts < 10:
                    upc = _generate_upc()
                    attempts += 1
                used_upcs.add(upc)
                upcs.append(upc)

            products.append(
                {
                    "id": uuid.uuid4(),
                    "canonical_name": canonical_name,
                    "category": category,
                    "subcategory": product_name,
                    "brand": brand,
                    "size": size_val,
                    "size_unit": default_unit,
                    "upc_variants": upcs,
                    "created_at": now,
                    "updated_at": now,
                }
            )

    return products
