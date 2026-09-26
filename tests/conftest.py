import os

os.environ["DATABASE_URL"] = "sqlite:///./test_eve_healthcare.db"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User

engine = create_engine(
    "sqlite:///./test_eve_healthcare.db",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, headers={"X-Skip-Rate-Limit": "1"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def signup(client, email="user@example.com", password="User@12345", full_name="Test User"):
    return client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
        },
    )


def login(client, email="user@example.com", password="User@12345"):
    response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    return response.json()["access_token"]


def login_json(client, email="user@example.com", password="User@12345"):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    return response.json()["access_token"]


def create_admin_user(db=None):
    close = False
    if db is None:
        db = TestingSessionLocal()
        close = True
    try:
        admin = User(
            email="admin@example.com",
            password_hash=hash_password("Admin@12345"),
            full_name="Admin User",
            is_admin=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin
    finally:
        if close:
            db.close()


def login_admin(client):
    create_admin_user()
    return login(client, email="admin@example.com", password="Admin@12345")


def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "X-Skip-Rate-Limit": "1"}
