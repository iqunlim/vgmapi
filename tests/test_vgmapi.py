#export PYTHONPATH="$PYTHONPATH:$PWD"

import pytest
import logging

from fastapi.testclient import TestClient

from api.main import create_app
from api.db import get_vgmdb

client = TestClient(create_app())

logger = logging.getLogger(__name__)

fake_db_entry = {
    "img": "file://test.png",
    "catalog_num": "SQEX-10589~91",
    "rating": 8,
    "game": "Test2212112",
    "description": "This game is cool and nice",
    "year_listened": "2024",
    "genre": "Rock",
    "tracks": [
        {
            "title":"Test",
            "runtime":"3:00",
        },
        {
            "title":"Test2",
            "runtime":"1:12"
        }
    ],
    "extras": {"personal":"343423"}
  }

fake_db_entry2 = {
    "img": "file://test.png",
    "catalog_num": "SQEX-10589~91",
    "rating": 8,
    "game": "Test22122",
    "description": "This game is cool and nice",
    "year_listened": "2024",
    "genre": "Metal1",
    "tracks": [
        {
            "title":"Test3",
            "runtime":"3:10",
        },
        {
            "title":"Test4",
            "runtime":"1:15"
        }
    ],
    "extras": {"personal":"34234242"}
}

fake_db = [fake_db_entry, fake_db_entry2]

@pytest.fixture
def database():
    yield get_vgmdb().__class__
    

@pytest.fixture
def mock_db_entry_response(monkeypatch, database):
    
    def mock_get_game(*args, **kwargs):
        return fake_db_entry
    
    
    monkeypatch.setattr(database, "query_game", mock_get_game)

def test_read_main():
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == {"Hello":"World"}
    

def test_get_vgm(mock_db_entry_response):
    
    response = client.get('/api/game/Test2212112')
    assert response.status_code == 200
    assert response.json() == fake_db_entry

    