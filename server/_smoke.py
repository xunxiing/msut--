import os, sys
sys.path.insert(0, os.getcwd())
from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)
resp = client.get("/api/auth/me")
print(resp.status_code, resp.text)
