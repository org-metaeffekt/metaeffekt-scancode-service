from fastapi.testclient import TestClient
from scancode_service import app

client = TestClient(app)

def test_fastapi():
    response = client.get("/scan//home/kai/projekte/metaeffekt/scancode-toolkit/samples/")
    assert response.status_code == 200
    assert response.json() == "/home/kai/projekte/metaeffekt/scancode-toolkit/samples/"
