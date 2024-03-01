import redis
import json
import os
#Configure redis here.
import logging

CONFIG_FILE = '/config/redis.json'

logger = logging.getLogger(__name__)

def get_redis(config_file: str=CONFIG_FILE) -> redis.Redis:
    """
    returns a redis.Redis object if the server can be connected to from the config file settings,
    if it cannot be connected to or if there is some other error it will return None.
    If local ENV API_NOCACHE=1 then it will return None. Used in the dockerfiles
    """
    if os.environ.get("API_NOCACHE", "0") == "1":
        return None
    
    with open(os.path.dirname(os.path.realpath(__file__)) + CONFIG_FILE) as config:
        settings = json.load(config)['redis_settings']
    try:
        return_obj = redis.Redis(**settings)
        return_obj.client_info() #handshake check to make sure redis is live.
        logger.info("Redis connection established to %s on port %s", settings.get('host'), settings.get('port'))
    except Exception:
        logger.error("Exception in connecting to redis database")
        return_obj = None
    return return_obj