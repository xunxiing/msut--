import os, sys
sys.path.insert(0, os.getcwd())
from fastapi.testclient import TestClient
from server.app import app
from server.db import run_migrations

run_migrations()

client = TestClient(app)

# Register
r = client.post("/api/auth/register", json={"username": "user1", "password": "secret123", "name": "张三"})
print("register", r.status_code, r.json())

# Me after register should be logged in (cookie set)
r = client.get("/api/auth/me")
print("me", r.status_code, r.json())

# Logout
r = client.post("/api/auth/logout")
print("logout", r.status_code, r.json())

# Login
r = client.post("/api/auth/login", json={"username": "user1", "password": "secret123"})
print("login", r.status_code, r.json())
