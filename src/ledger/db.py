"""The database: its tables and the connection to it."""

import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, String, create_engine, event
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
)
from sqlalchemy.types import TypeDecorator

# Where the database lives: a SQLite file called ledger.db in the folder where
# the program runs. Switching to another database would only change this line.
DATABASE_URL = "sqlite:///ledger.db"


class Money(TypeDecorator):
    """An amount: a Decimal in Python, a whole number of cents in the database."""

    impl = Integer
    cache_ok = True

    # Python -> database: -950.00 becomes -95000 cents. Anything smaller than
    # a cent is refused, so no money is ever lost by rounding.
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        cents = value * 100
        if cents != cents.to_integral_value():
            raise ValueError(f"{value} has fractions of a cent")
        return int(cents)

    # Database -> Python: -95000 cents becomes Decimal("-950.00").
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return Decimal(value).scaleb(-2)


class Base(DeclarativeBase):
    pass


# Table "accounts": every account is stored once, with a unique name.
class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    # One account has many transactions (one-to-many).
    rows: Mapped[list[TransactionRow]] = relationship(back_populates="account")


class TransactionRow(Base):
    """One row of the table `transactions`."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.date]
    description: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))
    amount: Mapped[Decimal] = mapped_column(Money)

    # Foreign key: each row stores the id of its account instead of repeating
    # the account's name. The database refuses an id that is not in accounts.
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))

    # The other side of Account.rows: row.account gives the Account object,
    # so the code never has to look up account_id by hand.
    account: Mapped[Account] = relationship(back_populates="rows")


# One engine for the whole program: it manages the connections to the file.
engine = create_engine(DATABASE_URL)


@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    """SQLite checks foreign keys only when asked to, once per connection."""
    dbapi_connection.execute("PRAGMA foreign_keys = ON")


def create_tables() -> None:
    """Creates the tables that don't exist yet. Existing tables are not changed."""
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
