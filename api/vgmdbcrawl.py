from fastapi import APIRouter, HTTPException
from bs4 import BeautifulSoup
from pydantic import BaseModel
from redis.exceptions import RedisError

import requests
import logging
import re
import datetime
from datetime import timedelta
from typing import Union

from api.db import Track, VGMEntry
from api.redisconfig import get_redis

vgmdbapi = APIRouter(prefix="/api/vgmdb")
logger = logging.getLogger(__name__)

class VGMDBPull(BaseModel):
    Title: str
    Game: str
    AlbumInfo: dict | None = None
    Tracks: dict | None = None
    Covers: list | None = None
    Credits: dict | None = None
    
    


#TODO: MORE REFACTOR(Turn this entire thing in to a dang object please) AND WRITE TESTS
@vgmdbapi.get('/{catalog}',response_model=Union[VGMDBPull, VGMEntry])
def get_game_info(catalog: str, convert: int = 0, nocache: int = 0):
    
    cached_flag = False
    return_json = {"Title":"N/A"}
    
    
    if nocache == 0:
        try:
            r = get_redis()
            cached_values = r.json().get(f'game:{catalog}')
        except RedisError:
            logger.error("Error connecting to redis database, skipping cache...")
            nocache = 1
        else:
            if cached_values:
                logger.info(f"Returned cached values for game:{catalog}")
                cached_flag = True
                return_json = cached_values
    else:
        logger.info("Skipping caching for %s", catalog)
    
    #START UNCACHED PULL AND FORMAT
    if not cached_flag:   
        try:
            soup = BeautifulSoup(
                requests.get(f'https://vgmdb.net/album/{catalog}').content, 
                'html.parser'
            )
            #Well if it fails....
            if next(soup.find('h1').stripped_strings) == 'System Message': 
                raise Exception
        except Exception:
            logger.exception("Exception in pulling vgmdb webpage")
            soup = BeautifulSoup('<p>Error: Invalid</p>', 'html.parser')
        else:
            return_json.update({'Title':next(soup.find('h1').stripped_strings)})
            logger.info("Converted vgmdb page: %s", catalog)
            
        game_name = soup.find('a', attrs={'href': re.compile(r'/product/[0-9]*')})
        if game_name:
            game_name = next(game_name.children).string
            return_json['Game'] = game_name
        else:
            #Hacky, TODO: Better way to do this than getting it from /product//
            return_json['Game'] = return_json['Title'].strip(" Original Soundtrack")

        album_info = {}
        try:
            album_table = soup.find("table", id='album_infobit_large').find_all('tr')
        except AttributeError:
            logger.error("album table not found")
        else:
            for row in album_table:
                if row.td is not None and not row.td.get('class', None):
                    values = [x for x in row.stripped_strings]
                    album_info.update({values[0]:values[1]})
            
        return_json.update({"AlbumInfo":album_info})
            
            
        titles_checked = []
        tracktable = {}
        try:
            tracklist = soup.find('div', id='tracklist')
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
                
            discs = tracklist.find_all('table', limit=len(titles_checked))
            for id, disc in enumerate(discs):
                title = titles_checked[id]
                tracklist_info = []
                for row in disc.find_all('tr'):
                    values = [val for val in row.stripped_strings]
                    tracklist_info.append({"title":values[1], "duration":values[2]})
                tracktable.update({title:tracklist_info})
            
        return_json.update({"Tracks":tracktable if tracktable else None})
        
        covers = soup.find('div', id="cover_gallery")
        if covers:    
            images = [
                img.get('href', None) \
                for img in covers.table.find_all('a')
            ]
        else:
            logger.info("No covers found.")
            images = []
        
        return_json.update({'Covers':images})

        credits_table = {}
        try:
            collapse_credits = soup.find('div', id="collapse_credits").table.find_all('tr')
        except AttributeError:
            logger.info("no credits found")
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
                    else:
                        if td.a is not None:
                            credits_list.extend([a_val.string for a_val in td.find_all('a')])
                        else:
                            credits_list.extend([str_val for str_val in td.stripped_strings])
                credits_table.update({credits_list[0]:", ".join(credits_list[1:])})
            
        return_json.update({"Credits":credits_table})
        
        #Caching
        if nocache == 0:
            r.json().set(f'game:{catalog}','$',return_json)
            r.expire(f'game:{catalog}',timedelta(minutes=30))

    #END UNCACHED PULL AND FORMAT
    #Convert to VGMDBEntry for use with the rest of things in db.py
    if convert == 1:
        try:
            list_of_tracks_for_vgmentry = []
            for key, value in return_json.get("Tracks", None).items():
                current_disc = key
            for id, dictionaries in enumerate(value):
                list_of_tracks_for_vgmentry.append(Track(disc=current_disc, track_id=id, title=dictionaries['title'], duration=dictionaries['duration']))
            
            one_cover = return_json.get("Covers", None)
            if one_cover:
                one_cover = one_cover[1]
            else:
                one_cover = None
            
            return VGMEntry(
                year_listened=int(datetime.date.today().strftime("%Y")),
                game=return_json['Game'],
                catalog_num=return_json['AlbumInfo']['Catalog Number'],
                rating=0,
                img=one_cover,
                description='TODO',
                tracks = list_of_tracks_for_vgmentry,
                extras=["TODO"],
            )
        except Exception:
            logger.exception("Error converting vgmdb page to VGMEntry database entry")
            raise HTTPException(status_code=500, detail="Error in conversion. Likely the page was not formatted correctly. Check your vgmdb id and try again.")

    return VGMDBPull(**return_json)
    
        


#TODO: Some sort of searching
#https://vgmdb.net/search?q=mother&type=album
#@vgmdbapi.get('{game}')
#def search_for_game(game: str):
    #pass

