from fastapi.testclient import TestClient
from api.main import create_app

import pytest
import requests

#requests.Response object mocking
class MockVGMDBRequest():

    @property
    def content(self):
        content = ""
        with open('./tests/examples/example-vgmdb-page.html') as file:
            for line in file:
                content += line
        return content
           
@pytest.fixture(autouse=True)
def no_requests_get(monkeypatch):
    
    def mock_get(*args, **kwargs):
        return MockVGMDBRequest()
    
    monkeypatch.setattr(requests, "get", mock_get)

@pytest.fixture
def fastapi_client():
    return TestClient(create_app())