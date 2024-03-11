import pytest
import json

from api.vgmdbcrawl import VGMDataForVGMAPI, VGMEntry

import fakeredis
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

##### 65091  
    
@pytest.fixture
def example_vgmdb_to_json():
    json_yield = open('./tests/examples/example-vgmdb-apireturn.json')
    yield json.load(json_yield)
    json_yield.close()
    
# currently unused    
@pytest.fixture
def example_db_to_json():

    json_yield = open('./tests/examples/example-db-apireturn.json')
    yield json.load(json_yield)
    json_yield.close()
    
@pytest.fixture
def vgmapi_obj() -> VGMDataForVGMAPI:
    return VGMDataForVGMAPI(65091)

@pytest.fixture()
def fake_redis() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis()

def test_fetch_vals_from_webpage(vgmapi_obj):
    
    vgmapi_obj.fetch_vals_from_webpage()
    assert isinstance(vgmapi_obj.soup, BeautifulSoup)
    assert vgmapi_obj.title == "NieR:Automata Original Soundtrack"
    
    with open('./tests/examples/example-vgmdb-page.html') as file:
        vgmapi_obj.fetch_vals_from_webpage(file)
        
    assert isinstance(vgmapi_obj.soup, BeautifulSoup)
    delattr(vgmapi_obj,"soup")
            
    with pytest.raises(TypeError) as excinfo:
        vgmapi_obj.fetch_vals_from_webpage({"Non":"Parsable"})
        assert "Custom content" in str(excinfo.value)
        vgmapi_obj.fetch_vals_from_webpage(None)
        assert "Custom content" in str(excinfo.value)
    

def test_title(vgmapi_obj):
    vgmapi_obj.soup = BeautifulSoup("<h1>Testing</h1>", "html.parser")
    assert vgmapi_obj.soup.find("h1").string == "Testing"
    assert vgmapi_obj.title == "Testing"
    delattr(vgmapi_obj,"title")
    vgmapi_obj.soup = BeautifulSoup("<h1>System Message</h1>", "html.parser")
    assert vgmapi_obj.title == "Not Found"
    delattr(vgmapi_obj,"title")
    vgmapi_obj.soup = 1
    assert vgmapi_obj.title == None
    delattr(vgmapi_obj,"title")
    delattr(vgmapi_obj,"soup")
    
def test_game(vgmapi_obj):
    vgmapi_obj.soup = BeautifulSoup("<p>Testing</p>", "html.parser")
    assert vgmapi_obj.game is None    
    delattr(vgmapi_obj, "game")
    delattr(vgmapi_obj, "title")
    vgmapi_obj.soup = BeautifulSoup("<h1>Testing123</h1>", "html.parser")
    assert vgmapi_obj.soup.find("h1").string == "Testing123"
    assert vgmapi_obj.title == "Testing123"
    assert vgmapi_obj.game == "Testing123"
    delattr(vgmapi_obj, "game")
    delattr(vgmapi_obj, "title")
    vgmapi_obj.soup = BeautifulSoup("<h1>Testing Original Soundtrack</h1>", "html.parser")
    assert vgmapi_obj.game == "Testing"  
    delattr(vgmapi_obj, "soup")
    delattr(vgmapi_obj, "title")
    delattr(vgmapi_obj, "game")
    
    
def test_albuminfo(vgmapi_obj, example_vgmdb_to_json):
    
    vgmapi_obj.fetch_vals_from_webpage()
    assert isinstance(vgmapi_obj.albuminfo, dict)
    assert vgmapi_obj.albuminfo.get("Barcode") == example_vgmdb_to_json.get("AlbumInfo").get("Barcode")
    assert len(vgmapi_obj.albuminfo) == 11
    delattr(vgmapi_obj,"albuminfo")
    vgmapi_obj.fetch_vals_from_webpage("<p>Test</p>")
    assert vgmapi_obj.albuminfo == {}
    
    
def test_tracks(vgmapi_obj, example_vgmdb_to_json):
    vgmapi_obj.fetch_vals_from_webpage()
    assert isinstance(vgmapi_obj.tracks, dict)
    for key, value in vgmapi_obj.tracks.items():
        assert isinstance(key, str)
        assert isinstance(value, list)
        for track in value:
            assert isinstance(track, dict)
            assert "title" in track
            
    assert vgmapi_obj.tracks["Disc 1 [SQEX-10589]"][0] == \
        example_vgmdb_to_json["Tracks"]["Disc 1 [SQEX-10589]"][0]
        
    delattr(vgmapi_obj, "soup")
    delattr(vgmapi_obj, "tracks")
    vgmapi_obj.fetch_vals_from_webpage("<p>Testing</p>")
    assert vgmapi_obj.tracks == {}

def test_covers(vgmapi_obj, example_vgmdb_to_json):
    vgmapi_obj.fetch_vals_from_webpage()
    assert isinstance(vgmapi_obj.covers, list)
    for cover in vgmapi_obj.covers:
        assert isinstance(cover, str)
    delattr(vgmapi_obj, "covers")
    vgmapi_obj.fetch_vals_from_webpage("<p>Testing</p>")
    assert vgmapi_obj.covers == []
    
def test_credits(vgmapi_obj):
    vgmapi_obj.fetch_vals_from_webpage()  
    assert isinstance(vgmapi_obj.credits, dict)
    for row in vgmapi_obj.credits:
        assert isinstance(row, str)
    assert vgmapi_obj.credits.get("All Music Produced by", None) == 'Keiichi Okabe'
    #TODO: Testing for JP language vs EN language
    #delattr(vgmapi_obj, "credits")
    #TODO: Check other table styles
        
def test_cache(vgmapi_obj, fake_redis):
    assert vgmapi_obj.get_cached_vals(fake_redis) == False
    assert isinstance(vgmapi_obj.get_cached_vals(fake_redis), bool)
    vgmapi_obj.fetch_vals_from_webpage()
    vgmapi_obj.set_cached_vals(fake_redis)
    assert isinstance(fake_redis.json().get(f'game:65091'), dict)
    assert vgmapi_obj.get_cached_vals(fake_redis) == True
    assert vgmapi_obj.title == "NieR:Automata Original Soundtrack"
    

def test_notes(vgmapi_obj):
    # TODO: Edit on implementation of feature
    with pytest.raises(NotImplementedError) as exinfo:
        this_will_throw_error = vgmapi_obj.notes
        assert "Notes have not been added" in exinfo.value

def test_get_game_info(fastapi_client: TestClient, example_vgmdb_to_json):
    
    response = fastapi_client.get("/api/vgmdb/65091")
    assert response.status_code == 200
    assert response.json()['Title'] == example_vgmdb_to_json['Title']
    
    response = fastapi_client.get("/api/vgmdb/65091", params={"convert":1})
    assert response.status_code == 200
