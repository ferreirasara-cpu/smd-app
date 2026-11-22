"""The command line: reads the arguments, calls storage and reports, prints."""

import argparse
import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ledger import db, reports, storage

DEFAULT_FILE = Path("data/transactions.csv")


def print_totals(totals: dict[str, Decimal]) -> None:
    for name, total in totals.items():
        print(f"{name:<10} {total:>10}")


def print_spending(spending: dict[str, Decimal]) -> None:
    table = Table(title="Spending by category")
    table.add_column("Category")
    table.add_column("EUR", justify="right")
    for category, total in spending.items():
        table.add_row(category, f"{total:,.2f}")
    Console().print(table)


def parse_amount(text: str) -> Decimal:
    """Converts an amount typed by the user, such as -12.50, into a Decimal."""
    # argparse does not understand decimal.InvalidOperation, so it is turned
    # into ArgumentTypeError, which argparse prints as a one-line usage error.
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise argparse.ArgumentTypeError(f"not an amount: {text!r}") from None
    # Decimal accepts "NaN" and "Infinity", which are not amounts of money.
    if not amount.is_finite():
        raise argparse.ArgumentTypeError(f"not an amount: {text!r}")
    return amount


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ledger", description="Balances and spending of your accounts."
    )
    # Subcommands, like git: each command gets its own parser and arguments.
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("balance", help="balance of each account")
    commands.add_parser("spending", help="spending by category")
    commands.add_parser("months", help="net change of each month")

    # "import" is a Python keyword, hence the trailing underscore.
    import_ = commands.add_parser("import", help="add the transactions of a CSV file")
    import_.add_argument("file", nargs="?", type=Path, default=DEFAULT_FILE)

    add = commands.add_parser("add", help="record one transaction")
    add.add_argument("account")
    add.add_argument("amount", type=parse_amount, help="negative for money going out")
    add.add_argument("category")
    add.add_argument("description")
    add.add_argument(
        "--date", type=datetime.date.fromisoformat, default=datetime.date.today()
    )
    return parser


def main() -> None:
    args = make_parser().parse_args()
    db.create_tables()

    # One session for the whole command; "with" closes it at the end.
    with db.get_session() as session:
        if args.command == "import":
            count = storage.import_csv(session, args.file)
            print(f"Imported {count} transactions from {args.file}")
        elif args.command == "add":
            try:
                storage.add_transaction(
                    session,
                    args.account,
                    args.amount,
                    args.category,
                    args.description,
                    args.date,
                )
            except ValueError as error:
                # A broken rule becomes one clean line and exit code 1,
                # instead of a traceback.
                raise SystemExit(f"ledger: {error}") from None
            print(f"Added {args.amount} to {args.account}")
        else:
            # The reports don't know where the transactions come from:
            # before it was the CSV file, now it is the database.
            transactions = storage.load_transactions(session)
            if args.command == "balance":
                print_totals(reports.balances(transactions))
            elif args.command == "spending":
                print_spending(reports.spending_by_category(transactions))
            else:
                print_totals(reports.net_by_month(transactions))
