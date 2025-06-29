
# src/database/custom_types.py
import datetime
from sqlalchemy import DateTime, TypeDecorator
from sqlalchemy.dialects.sqlite import DATETIME as SQLITE_DATETIME

class UTCDateTime(TypeDecorator):
    """A custom SQLAlchemy type to store timezone-aware datetime objects in UTC.

    as naive datetime objects in a SQLite database.
    """
    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'sqlite':
            return dialect.type_descriptor(SQLITE_DATETIME())
        else:
            return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value: datetime.datetime | None, dialect) -> datetime.datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            # Assume naive datetime is in local timezone and convert to UTC
            value = value.astimezone(datetime.timezone.utc)
        return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime.datetime | None, dialect) -> datetime.datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.timezone.utc)
        return value.astimezone(datetime.timezone.utc)
