from fastapi.testclient import TestClient
from api.main import create_app
from os.path import exists
from urllib.request import urlopen

import pytest
import requests

#requests.Response object mocking
class MockVGMDBRequest():

    @property
    def content(self):
        if not exists('./tests/examples/example-vgmdb-page.html'):
            file = urlopen('https://vgmdb.net/album/65091')
            html_bytes = file.read()
            html = html_bytes.decode("utf-8")
            f = open('./tests/examples/example-vgmdb-page.html', 'w')
            f.writelines(html)
            f.close()
            return html
        else:
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