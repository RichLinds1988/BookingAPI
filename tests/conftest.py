import pytest
from unittest.mock import MagicMock, patch
from app import create_app, db as _db
from app.models import User, Resource, Booking
from flask_jwt_extended import create_access_token
from datetime import datetime, timedelta


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = "test-secret"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    SECRET_KEY = "test-flask-secret"
    REDIS_URL = "redis://localhost:6379/0"
    CACHE_TTL = 30
    RATELIMIT_ENABLED = False


@pytest.fixture(scope="session")
def app():
    with patch("app.redis_lib.from_url") as mock_redis:
        mock_redis.return_value = MagicMock()
        application = create_app(TestConfig)
    with patch("app.middleware.cache.redis_client") as mock_cache_redis:
        mock_cache_redis.get.return_value = None
        mock_cache_redis.setex.return_value = True
        mock_cache_redis.keys.return_value = []
        yield application


@pytest.fixture(scope="function")
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app, db):
    with patch("app.middleware.cache.redis_client") as mock_cache_redis:
        mock_cache_redis.get.return_value = None
        mock_cache_redis.setex.return_value = True
        mock_cache_redis.keys.return_value = []
        yield app.test_client()


@pytest.fixture
def test_user(db, app):
    with app.app_context():
        user = User(name="Test User", email="test@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def auth_headers(app, test_user):
    with app.app_context():
        token = create_access_token(identity=str(test_user.id))
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture
def test_resource(db, app):
    with app.app_context():
        resource = Resource(name="Boardroom A", description="Main boardroom", capacity=10)
        db.session.add(resource)
        db.session.commit()
        db.session.refresh(resource)
        return resource


@pytest.fixture
def future_times():
    start = datetime.now() + timedelta(days=1)
    end = start + timedelta(hours=1)
    return start.strftime("%Y-%m-%dT%H:%M:%S"), end.strftime("%Y-%m-%dT%H:%M:%S")
