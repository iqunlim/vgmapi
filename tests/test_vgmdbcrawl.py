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
    assert vgmapi_obj.covers == example_vgmdb_to_json.get("Covers", None)
    delattr(vgmapi_obj, "covers")
    vgmapi_obj.fetch_vals_from_webpage("<p>Testing</p>")
    assert vgmapi_obj.covers == []
    
def test_credits(vgmapi_obj):
    vgmapi_obj.fetch_vals_from_webpage()  
    assert isinstance(vgmapi_obj.credits, dict)
    for row in vgmapi_obj.credits:
        assert isinstance(row, str)
    assert vgmapi_obj.credits.get("All Music Produced by", None) == 'Keiichi Okabe'
    assert vgmapi_obj.credits.get("Lyrics", None) == "YOKO TARO, J'Nique Nicole"
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
    assert response.json() == example_vgmdb_to_json
    
    response = fastapi_client.get("/api/vgmdb/65091", params={"convert":1})
    assert response.status_code == 200
    assert response.json() == {
    "rating": 0,
    "description": "Temp",
    "extras": [
        {}
    ],
    "year_listened": 2024,
    "catalog_num": "SQEX-10589~91",
    "game": "NieR: Automata",
    "img": "https://medium-media.vgm.io/albums/19/65091/65091-1c5e756fbddb.png",
    "tracks": [
        {
            "disc": "Disc 1 [SQEX-10589]",
            "track_id": 0,
            "title": "Significance - Nothing",
            "duration": "2:39"
        },
        {
            "disc": "Disc 1 [SQEX-10589]",
            "track_id": 1,
            "title": "City Ruins - Rays of Light",
            "duration": "6:22"
        },
        {
            "disc": "Disc 1 [SQEX-10589]",
            "track_id": 2,
            "title": "Peaceful Sleep",
            "duration": "6:50"
        },
        {
            "disc": "Disc 1 [SQEX-10589]",
            "track_id": 3,
            "title": "Memories of Dust",
            "duration": "5:29"
        },
        {
            "disc": "Disc 1 [SQEX-10589]",
            "track_id": 4,
            "title": "Birth of a Wish",
            "duration": "4:40"
        },
        {
            "disc": "Disc 1 [SQEX-10589]",
            "track_id": 5,
            "title": "The Color of Depression",
            "duration": "3:17"
        },
        {
            "disc": "Disc 1 [SQEX-10589]",
            "track_id": 6,
            "title": "Amusement Park",
            "duration": "6:19"
        },
        {
            "disc": "Disc 1 [SQEX-10589]",
            "track_id": 7,
            "title": "A Beautiful Song",
            "duration": "4:05"
        },
        {
            "disc": "Disc 1 [SQEX-10589]",
            "track_id": 8,
            "title": "Voice of no Return - Guitar",
            "duration": "3:51"
        },
        {
            "disc": "Disc 1 [SQEX-10589]",
            "track_id": 9,
            "title": "Grandma - Destruction",
            "duration": "5:31"
        },
        {
            "disc": "Disc 1 [SQEX-10589]",
            "track_id": 10,
            "title": "Faltering Prayer - Dawn Breeze",
            "duration": "3:12"
        },
        {
            "disc": "Disc 1 [SQEX-10589]",
            "track_id": 11,
            "title": "Emil's Shop",
            "duration": "5:28"
        },
        {
            "disc": "Disc 1 [SQEX-10589]",
            "track_id": 12,
            "title": "Treasured Times",
            "duration": "3:46"
        },
        {
            "disc": "Disc 1 [SQEX-10589]",
            "track_id": 13,
            "title": "Vague Hope - Cold Rain",
            "duration": "3:36"
        },
        {
            "disc": "Disc 1 [SQEX-10589]",
            "track_id": 14,
            "title": "Weight of the World English Version",
            "duration": "5:44"
        },
        {
            "disc": "Disc 2 [SQEX-10590]",
            "track_id": 0,
            "title": "Significance",
            "duration": "2:39"
        },
        {
            "disc": "Disc 2 [SQEX-10590]",
            "track_id": 1,
            "title": "City Ruins - Shade",
            "duration": "6:01"
        },
        {
            "disc": "Disc 2 [SQEX-10590]",
            "track_id": 2,
            "title": "End of the Unknown",
            "duration": "4:31"
        },
        {
            "disc": "Disc 2 [SQEX-10590]",
            "track_id": 3,
            "title": "Voice of no Return - Normal",
            "duration": "2:53"
        },
        {
            "disc": "Disc 2 [SQEX-10590]",
            "track_id": 4,
            "title": "Pascal",
            "duration": "4:47"
        },
        {
            "disc": "Disc 2 [SQEX-10590]",
            "track_id": 5,
            "title": "Forest Kingdom",
            "duration": "5:52"
        },
        {
            "disc": "Disc 2 [SQEX-10590]",
            "track_id": 6,
            "title": "Dark Colossus - Kaiju",
            "duration": "6:06"
        },
        {
            "disc": "Disc 2 [SQEX-10590]",
            "track_id": 7,
            "title": "Copied City",
            "duration": "3:59"
        },
        {
            "disc": "Disc 2 [SQEX-10590]",
            "track_id": 8,
            "title": "Wretched Weaponry:Medium/Dynamic",
            "duration": "7:04"
        },
        {
            "disc": "Disc 2 [SQEX-10590]",
            "track_id": 9,
            "title": "Possessed by Disease",
            "duration": "5:02"
        },
        {
            "disc": "Disc 2 [SQEX-10590]",
            "track_id": 10,
            "title": "Broken Heart",
            "duration": "3:30"
        },
        {
            "disc": "Disc 2 [SQEX-10590]",
            "track_id": 11,
            "title": "Wretched Weaponry:Quiet",
            "duration": "3:07"
        },
        {
            "disc": "Disc 2 [SQEX-10590]",
            "track_id": 12,
            "title": "Mourning",
            "duration": "4:51"
        },
        {
            "disc": "Disc 2 [SQEX-10590]",
            "track_id": 13,
            "title": "Dependent Weakling",
            "duration": "5:06"
        },
        {
            "disc": "Disc 2 [SQEX-10590]",
            "track_id": 14,
            "title": "Weight of the World Kowaretasekainouta",
            "duration": "5:44"
        },
        {
            "disc": "Disc 3 [SQEX-10591]",
            "track_id": 0,
            "title": "Rebirth & Hope",
            "duration": "0:37"
        },
        {
            "disc": "Disc 3 [SQEX-10591]",
            "track_id": 1,
            "title": "War & War",
            "duration": "4:32"
        },
        {
            "disc": "Disc 3 [SQEX-10591]",
            "track_id": 2,
            "title": "Crumbling Lies - Front",
            "duration": "3:26"
        },
        {
            "disc": "Disc 3 [SQEX-10591]",
            "track_id": 3,
            "title": "Widespread Illness",
            "duration": "3:18"
        },
        {
            "disc": "Disc 3 [SQEX-10591]",
            "track_id": 4,
            "title": "Fortress of Lies",
            "duration": "2:49"
        },
        {
            "disc": "Disc 3 [SQEX-10591]",
            "track_id": 5,
            "title": "Vague Hope - Spring Rain",
            "duration": "4:40"
        },
        {
            "disc": "Disc 3 [SQEX-10591]",
            "track_id": 6,
            "title": "Song of the Ancients - Atonement",
            "duration": "5:09"
        },
        {
            "disc": "Disc 3 [SQEX-10591]",
            "track_id": 7,
            "title": "Blissful Death",
            "duration": "2:36"
        },
        {
            "disc": "Disc 3 [SQEX-10591]",
            "track_id": 8,
            "title": "Emil - Despair",
            "duration": "4:46"
        },
        {
            "disc": "Disc 3 [SQEX-10591]",
            "track_id": 9,
            "title": "Faltering Prayer - Starry Sky",
            "duration": "3:44"
        },
        {
            "disc": "Disc 3 [SQEX-10591]",
            "track_id": 10,
            "title": "Alien Manifestation",
            "duration": "6:27"
        },
        {
            "disc": "Disc 3 [SQEX-10591]",
            "track_id": 11,
            "title": "The Tower",
            "duration": "7:43"
        },
        {
            "disc": "Disc 3 [SQEX-10591]",
            "track_id": 12,
            "title": "Bipolar Nightmare",
            "duration": "5:00"
        },
        {
            "disc": "Disc 3 [SQEX-10591]",
            "track_id": 13,
            "title": "The Sound of the End",
            "duration": "5:26"
        },
        {
            "disc": "Disc 3 [SQEX-10591]",
            "track_id": 14,
            "title": "Weight of the World Nouveau - FR Version",
            "duration": "5:47"
        },
        {
            "disc": "Disc 3 [SQEX-10591]",
            "track_id": 15,
            "title": "Weight of the World the End of YoRHa",
            "duration": "5:39"
        }
    ]
}
