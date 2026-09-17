import os
os.environ["DATABASE_URL"]="sqlite:///./test_droneoptai.db"
from fastapi.testclient import TestClient
from app.main import app

def test_health():
    with TestClient(app) as c:
        r=c.get('/health')
        assert r.status_code==200
        assert r.json()['status']=='ok'
