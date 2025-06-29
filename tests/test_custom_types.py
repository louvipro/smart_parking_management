import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, Column, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
from src.shared.custom_types import UTCDateTime
from unittest.mock import MagicMock

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

def test_utc_datetime_process_bind_param_naive_explicit():
    utc_type = UTCDateTime()
    naive_dt = datetime(2023, 1, 1, 10, 0, 0) # Naive datetime
    
    # Mock a dialect that is not sqlite to hit the else branch in load_dialect_impl
    mock_dialect = MagicMock()
    mock_dialect.name = 'postgresql'
    mock_dialect.type_descriptor.return_value = MagicMock()

    # Test process_bind_param with naive datetime
    processed_value = utc_type.process_bind_param(naive_dt, mock_dialect)
    assert processed_value.tzinfo is None # Should be naive after replace(tzinfo=None)
    assert processed_value == naive_dt.astimezone(timezone.utc).replace(tzinfo=None)

def test_utc_datetime_process_result_value_naive_explicit():
    utc_type = UTCDateTime()
    # Simulate a naive datetime coming from the database
    naive_db_dt = datetime(2023, 1, 1, 10, 0, 0) 
    
    # Mock a dialect that is not sqlite
    mock_dialect = MagicMock()
    mock_dialect.name = 'postgresql'
    mock_dialect.type_descriptor.return_value = MagicMock()

    # Test process_result_value with naive datetime from DB
    processed_value = utc_type.process_result_value(naive_db_dt, mock_dialect)
    assert processed_value.tzinfo == timezone.utc # Should be UTC aware
    assert processed_value == naive_db_dt.replace(tzinfo=timezone.utc)

def test_utc_datetime_load_dialect_impl_non_sqlite():
    utc_type = UTCDateTime()
    mock_dialect = MagicMock()
    mock_dialect.name = 'postgresql'
    mock_dialect.type_descriptor.return_value = "mock_type_descriptor"

    result = utc_type.load_dialect_impl(mock_dialect)
    assert result == "mock_type_descriptor"
    mock_dialect.type_descriptor.assert_called_once()
    args, kwargs = mock_dialect.type_descriptor.call_args
    assert isinstance(args[0], UTCDateTime.impl)
    assert args[0].timezone is True