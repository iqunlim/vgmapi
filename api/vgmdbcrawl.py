from fastapi import APIRouter, HTTPException, status
from bs4 import BeautifulSoup
from pydantic import BaseModel
from redis.exceptions import RedisError

import redis
import requests
import logging
import re
import datetime

from datetime import timedelta
from typing import Union
from functools import cached_property

from api.db import Track, VGMEntry
from api.redisconfig import get_redis


VGMDB_ALBUM_URL = "https://vgmdb.net/album/"

vgmdbapi = APIRouter(prefix="/api/vgmdb")
logger = logging.getLogger(__name__)

class ReadOnlyPropertyException(Exception):
    pass

class VGMDBException(Exception):
    def __init__(self, catalog: int) -> None:
        self.return_str = f"Exception raised on vgmdb page: {catalog}"
        
    def __str__(self) -> str:
        return self.return_str
    
class VGMDBData:
    
    def __init__(self, catalog_id: str) -> None:
        
        self.catalog = catalog_id
        self.soup = None
            
    def __str__(self):
        return f"VGMDBData of page: {self.catalog}"
    
    #TODO: __repr__
    
    def fetch_vals_from_webpage(self, content = None) -> None:
        """
        Creates the beautifulsoup object from the designated VGMDB album ID
        content: optional, Set this to directly get content from anything \
        that beautifulsoup can parse. Typically unused outside of debugging.
        and will throw errors if you utilize it incorrectly.
        """
        if content:
            try:
                self.soup = BeautifulSoup(content, 'html.parser')
            except Exception:
                raise Exception
        else:
            try:
                temp = requests.get(f'{VGMDB_ALBUM_URL}{self.catalog}').content
            except Exception:
                temp = f"<h1>ERROR on page {VGMDB_ALBUM_URL}{self.catalog}</h1>"
                logger.error("Error on request of page %s", self.catalog)
            
            try:
                self.soup = BeautifulSoup(temp, 'html.parser')
            except Exception:
                logger.exception("Error in VGMPageData.as_soup")
                self.soup = BeautifulSoup("<h1>Error</h1>", 'html.parser')
            
    @cached_property
    def title(self):
        value = next(self.soup.find('h1').stripped_strings)
        if value == "System Message":
            return "Not Found"
        return value
    
    @cached_property
    def game(self):
        game_name = self.soup.find('a', attrs={'href': re.compile(r'/product/[0-9]*')})
        if game_name:
            return next(game_name.children).string
        else:
            #Hacky, TODO: Better way to do this than getting it from /product/
            if self.title:
                return self.title.lstrip(" Original Soundtrack")
            else:
                return None
    
    @cached_property
    def albuminfo(self):
        album_info = {}
        try:
            album_table = self.soup.find("table", id='album_infobit_large').find_all('tr')
        except AttributeError:
            logger.error("album table not found")
        else:
            for row in album_table:
                if row.td is not None and not row.td.get('class', None):
                    values = [x for x in row.stripped_strings]
                    album_info.update({values[0]:values[1]})
        return album_info
    
    @cached_property
    def tracks(self):
        titles_checked = []
        tracktable = {}
        try:
            tracklist = self.soup.find('div', id='tracklist')
            if tracklist is None:
                raise AttributeError
        except AttributeError:
            logger.error("album table not found")
        else:
            #setting up the titles list for later and
            #checking to make sure that it doesnt iterate to the next
            #language or whatever, if theres repeats its on the next tab.
            #TODO: Better way to do this?
            for title in tracklist.find_all('b'):
                if title.string not in titles_checked:
                    titles_checked.append(title.string)
                else:
                    break
            # Don't look at this too hard. Needs refactoring but it works for the variety of tables ive seen...so far    
            discs = tracklist.find_all('table', limit=len(titles_checked))
            for id, disc in enumerate(discs):
                title = titles_checked[id]
                tracklist_info = []
                last_row = -1
                for row in disc.find_all('tr'):
                    values = [val for val in row.stripped_strings]
                    # TODO: Handle subtables? I'll have to redo this entire pull because vgmdb pulls dont make much sense
                    if len(values) >= 3:
                        tracklist_info.append({"title":values[1], "duration":values[2]})
                        last_row += 1
                    else:
                        test_str = [val for val in row.strings]
                        # Hacky? can't wait to see where this blows up next, VGMDB tables are mysterious. . . 
                        if test_str[3] != "\n": 
                            tracklist_info.append({"title":values[1]})
                            last_row += 1
                        else:
                            try:
                                if not tracklist_info[last_row].get("subtracks", None):
                                    tracklist_info[last_row]['subtracks'] = []
                                tracklist_info[last_row]["subtracks"].append(values[1])
                            except IndexError:
                                logger.error("Index out of range for tracks error, returning {}")
                                return {} 
                    tracktable.update({title:tracklist_info})
        return tracktable
    
    @cached_property
    def covers(self):
        covers = self.soup.find('div', id="cover_gallery")
        if covers:    
            return [
                img.get('href', None) \
                for img in covers.table.find_all('a')
            ]
        else:
            logger.info("No covers found.")
            return []
    
    @cached_property
    def credits(self):
        credits_table = {}
        try:
            collapse_credits = self.soup.find('div', id="collapse_credits").table.find_all('tr')
        except AttributeError:
            logger.info("No credits found")
        else:
            for row in collapse_credits:
                # In albums with multiple languages, without all this logic, you get a ton of junk that you dont want and its all weirdly out of order
                # This logic tree is the only way I found to get everything I want in the language I want without blowing everything to bits...
                # ...on every single varied version of the weird vgmdb tables. Why are vgmdb tables like this....
                # TODO: Modify the existing soup object with various methods for normalization? I don't know if that would be faster....
                credits_list = []
                for td in row.find_all('td'):
                    if td.find('span', attrs={'lang':'en'}):
                        credits_list.extend([all.string for all in td.find_all('span', lang='en')])
                    #TODO: Handle different languages. There are some albums which have 0 other languages and this will need to be accounted for
                    else:
                        if td.a is not None:
                            credits_list.extend([a_val.string for a_val in td.find_all('a')])
                        else:
                            credits_list.extend([str_val for str_val in td.stripped_strings])
                credits_table.update({credits_list[0]:", ".join(credits_list[1:])})
            
        return credits_table
    
    @cached_property
    def notes(self):
        raise NotImplementedError
        
    def get_cached_vals(self, redis_obj: redis.Redis) -> bool:
        # Returns true if cached loaded else return false
        cached_values = redis_obj.json().get(f'game:{self.catalog}')
        if cached_values:
            self.soup = BeautifulSoup('<h1>Cached VGMDB Data</h1>', 'html.parser') #Some default.
            self.title = cached_values.get('Title', None)
            self.game = cached_values.get('Game', None)
            self.albuminfo = cached_values.get('AlbumInfo', None)
            self.tracks = cached_values.get('Tracks', None)
            self.covers = cached_values.get('Covers', None)
            self.credits = cached_values.get('Credits', None)
            #self.notes = None #Not implemented yet
            
            info_str = f"Returned cached values for game:{self.catalog}"
            logger.info(info_str)
            
            return True
        else:
            return False
            
    #TODO: Set cache based off of attributes and not some passed-in data dictionary
    def set_cached_vals(self, redis_obj: redis.Redis, timelimit: datetime.timedelta = 30) -> None:
        try:
            data = {
                "Title":self.title,
                "Game":self.game,
                "AlbumInfo":self.albuminfo,
                "Tracks":self.tracks,
                "Covers":self.covers,
                "Credits": self.credits,
                #"Notes":self.notes, not implemented
            }
            redis_obj.json().set(f'game:{self.catalog}','$',data)
            redis_obj.expire(f'game:{self.catalog}',timedelta(minutes=timelimit))
        except RedisError:
            logger.error("Redis error in setting the cache:")
            logger.error("data object: %s", str(data))
        except Exception:
            logger.exception("Miscellaneous error in set_cached_values")
        else:
            logger.info("Set cache for %s", self.catalog)
            
class VGMDBPydantic(BaseModel):
    Title: str
    Game: str
    AlbumInfo: dict | None = None
    Tracks: dict | None = None
    Covers: list | None = None
    Credits: dict | None = None
    
# Specifically conversion from vgmdb data to things that I need in this api.                
class VGMDataForVGMAPI(VGMDBData):
    def __init__(self, catalog_id: str) -> None:
        super().__init__(catalog_id)
        
    def as_pydantic(self) -> VGMDBPydantic:
        return VGMDBPydantic(
            Title=self.title,
            Game=self.game, 
            AlbumInfo=self.albuminfo, 
            Tracks=self.tracks, 
            Covers=self.covers,
            Credits=self.credits
        )
        
    def as_db_entry(self, rating:int, description:str = None, year_listened: int = None, **kwargs) -> VGMEntry:
        
        #Convert list of list of dictionaries to [Track(), Track(),]
        #probaby convertable to a list comprehension but it would be pretty unreadable and dense.
        list_of_tracks_for_vgmentry = []
        for key, value in self.tracks.items():
            current_disc = key
            for id, dictionaries in enumerate(value):
                list_of_tracks_for_vgmentry.append(Track(disc=current_disc, 
                                                         track_id=id, 
                                                         title=dictionaries['title'], 
                                                         duration=dictionaries['duration']
                                                        )
                                                   )
            
        return VGMEntry(
            rating=rating,
            description=description,
            year_listened=int(datetime.date.today().strftime("%Y")) if year_listened is None else year_listened,
            catalog_num=self.catalog,
            game = self.game,
            img = self.covers[0],
            tracks = list_of_tracks_for_vgmentry,
            extras = [kwargs]
        )
        
def get_vgmdbdata(catalog_id: str):
    return VGMDataForVGMAPI(catalog_id)
        

@vgmdbapi.get('/{catalog}',response_model=Union[VGMDBPydantic, VGMEntry])
def get_game_info(catalog: str, convert: int = 0, cache_time_in_minutes=30, nocache: int = 0):
    
    vgmdata = get_vgmdbdata(catalog)
    redis_obj = get_redis()
    
    if nocache == 0 and redis_obj is not None:
        is_cached = vgmdata.get_cached_vals(redis_obj)
        if not is_cached:
            logger.info("No cache found for %s", catalog)
            vgmdata.fetch_vals_from_webpage()
            vgmdata.set_cached_vals(redis_obj, timelimit=cache_time_in_minutes)
    else:
        logger.info("No cache set for %s", catalog)
        vgmdata.fetch_vals_from_webpage()
        
    if convert == 1:
        return vgmdata.as_db_entry(rating=0, description="Temp", year_listened=2024)
    else:
        return vgmdata.as_pydantic()