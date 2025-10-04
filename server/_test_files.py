import os, sys
sys.path.insert(0, os.getcwd())
from io import BytesIO
from fastapi.testclient import TestClient
from server.app import app
from server.db import run_migrations

run_migrations()
client = TestClient(app)

# Ensure a user exists and logged in
client.post("/api/auth/register", json={"username": "user2", "password": "secret123", "name": "李四"})
client.post("/api/auth/login", json={"username": "user2", "password": "secret123"})

# Create resource
r = client.post("/api/resources", data={"title": "Sample Doc", "description": "desc", "usage": "use"})
print("create", r.status_code, r.json())
rid = r.json()["id"]

# Upload a file
files = {"files": ("test.txt", BytesIO(b"hello world"), "text/plain")}
r = client.post("/api/files/upload", data={"resourceId": str(rid)}, files=files)
print("upload", r.status_code, r.json())

# List my resources
r = client.get("/api/my/resources")
print("my", r.status_code, len(r.json().get("items", [])))

# Get resource by slug
slug = client.get("/api/resources").json()["items"][0]["slug"]
r = client.get(f"/api/resources/{slug}")
print("get", r.status_code, bool(r.json().get("files")))

