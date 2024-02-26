from fastapi import (
    FastAPI, status, HTTPException, APIRouter, Path
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import logging.config
import json
import os
import socket

from uvicorn.workers import UvicornWorker

from typing import Annotated, Union


import typer

from api.db import get_vgmdb, VGMInfo, VGMEntry
from api.vgmdbcrawl import vgmdbapi, get_game_info

#TODO: Figure out why my default logging configuration just straight up does not work at all.

logger = logging.getLogger(__name__)

routerv1 = APIRouter(prefix="/api")

#uncomment when production time comes
'''from uvicorn.workers import UvicornWorker
class MyUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {
        "log_config": "/app/config/logging.json",
    }'''

def create_app() -> FastAPI:
    
    app = FastAPI(
        docs_url="/api/docs", 
        redoc_url=None,
    )
    
    with open(os.path.dirname(os.path.realpath(__file__)) + '/config/logging.json') as config_in:
        logging_config = json.load(config_in)   
    logging.config.dictConfig(config=logging_config)

    
    @app.get('/', status_code=status.HTTP_200_OK)
    async def root():
        return {"Hello":"World"}
    
    @app.get('/test')
    async def testing():
        return {"Hostname":socket.gethostname()}
    
    @routerv1.get('/game/{game_name}', response_model=Union[VGMEntry, dict])
    def get_game_api(game_name: Annotated[str, Path()]):
        try:
            db = get_vgmdb()
            response = db.query_game(game_name)
        except Exception as e:
            logger.exception("Exception occured in get_year_api")
            raise HTTPException(status_code=500, detail="Database Error")
        return response
    
    @routerv1.get('/year/{year}', response_model=list[VGMEntry])
    def get_year_api(year: str):
        db = get_vgmdb()
        try:
            response = db.query_year(year)
        except Exception as e:
            logger.exception("Exception occured in get_year_api")
            raise HTTPException(status_code=500, detail="Database Error")
        else:
            if response == []:
                raise HTTPException(status_code=404, detail="Item not found")
            return response
        
    @routerv1.put('/update', response_model=VGMEntry)
    def update_game_api(data: VGMEntry):
        try:
            db = get_vgmdb()
            response = db.update(data)
        except Exception as e:
            logger.exception("Exception occured in update_game_api")
            raise HTTPException(status_code=500, detail="Database Error")
        else:
            return response
        
    @routerv1.post('/rawadd', response_model=VGMEntry)
    def add_vgm_entry(data: VGMEntry):
        try:
            db = get_vgmdb()
            response = db.add(data)
        except Exception as e:
            logger.exception("Exception occured in get_year_api")
        else:
            return data
    
    @routerv1.delete('/delete', response_model=VGMEntry)
    def delete_game_api(data: VGMEntry):
        try:
            db = get_vgmdb()
            response = db.delete(data)
        except Exception as e:
            logger.exception("Exception occured in delete_game_api")
            raise HTTPException(status_code=500, detail="Database Error")
        else:
            return response
        
    @routerv1.post('/add/{catalog}')
    def add_game_to_db_from_vgmdb(catalog:str, data: VGMInfo):
        try:
            response = get_game_info(catalog, convert=1)
            logger.info("Response: %s", str(response))
            response.rating = data.rating
            response.description = data.description if data.description else "No Description"
            response.extras = data.extras if data.extras else None

            
            db = get_vgmdb()
            db.add(response)
            
        except:
            logger.exception("Error in getting game info from vgmdb")
            return {"Error":"Failure"}
        return response
    
        
    app.include_router(routerv1)
    app.include_router(vgmdbapi)
    return app

if __name__ == "__main__":
    uvicorn.run("api.main:create_app", factory=True, port=5000, reload=True, access_log=False)