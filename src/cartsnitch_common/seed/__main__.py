"""Entry point for `python -m cartsnitch_common.seed` and `cartsnitch-seed` CLI."""

import argparse
import sys

from cartsnitch_common.seed.config import SEED_VALUE


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cartsnitch-seed",
        description="Generate deterministic seed data for the CartSnitch dev environment.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help=(
            "PostgreSQL connection URL (sync driver). "
            "Defaults to CARTSNITCH_DATABASE_URL_SYNC env var or built-in default."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned record counts without writing to the database.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SEED_VALUE,
        help=f"Random seed for deterministic output (default: {SEED_VALUE}).",
    )

    args = parser.parse_args()

    try:
        from cartsnitch_common.seed.runner import run_seed

        run_seed(
            database_url=args.database_url,
            seed_value=args.seed,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
