import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, Column, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
from src.database.custom_types import UTCDateTime

Base = declarative_base()

class TestModel(Base):
    __tablename__ = "test_table"
    id = Column(Integer, primary_key=True)
    utc_datetime_col = Column(UTCDateTime)

@pytest.fixture(scope="function")
def db_session_custom_types():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)

def test_utc_datetime_aware_to_db_and_back(db_session_custom_types):
    session = db_session_custom_types
    now_aware = datetime.now(timezone.utc).replace(microsecond=0)

    instance = TestModel(utc_datetime_col=now_aware)
    session.add(instance)
    session.commit()

    retrieved_instance = session.query(TestModel).first()
    assert retrieved_instance.utc_datetime_col == now_aware
    assert retrieved_instance.utc_datetime_col.tzinfo == timezone.utc

def test_utc_datetime_naive_to_db_and_back(db_session_custom_types):
    session = db_session_custom_types
    # Naive datetime, assume it's local and convert to UTC
    now_naive = datetime.now().replace(microsecond=0)
    now_utc_expected = now_naive.astimezone(timezone.utc)

    instance = TestModel(utc_datetime_col=now_naive)
    session.add(instance)
    session.commit()

    retrieved_instance = session.query(TestModel).first()
    assert retrieved_instance.utc_datetime_col == now_utc_expected
    assert retrieved_instance.utc_datetime_col.tzinfo == timezone.utc

def test_utc_datetime_none_value(db_session_custom_types):
    session = db_session_custom_types

    instance = TestModel(utc_datetime_col=None)
    session.add(instance)
    session.commit()

    retrieved_instance = session.query(TestModel).first()
    assert retrieved_instance.utc_datetime_col is None

def test_utc_datetime_different_timezone_to_db_and_back(db_session_custom_types):
    session = db_session_custom_types
    # Create a timezone object for a different timezone (e.g., EST = UTC-5)
    est = timezone(timedelta(hours=-5))
    now_est = datetime.now(est).replace(microsecond=0)
    now_utc_expected = now_est.astimezone(timezone.utc)

    instance = TestModel(utc_datetime_col=now_est)
    session.add(instance)
    session.commit()

    retrieved_instance = session.query(TestModel).first()
    assert retrieved_instance.utc_datetime_col == now_utc_expected
    assert retrieved_instance.utc_datetime_col.tzinfo == timezone.utc
