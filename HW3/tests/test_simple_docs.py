import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.simple_docs import add_custom_docs

def test_add_custom_docs():
    """Тест добавления пользовательской документации"""

    app = FastAPI(title="Test App")
    
    add_custom_docs(app)

    assert app.docs_url is None
    
    routes = [route.path for route in app.routes]
    assert "/docs" in routes
    

    client = TestClient(app)
    

    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "swagger" in response.text.lower()