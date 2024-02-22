import redis
import json
import os
#Configure redis here.

CONFIG_FILE = '/config/redis.json'

def get_redis(config_file: str=CONFIG_FILE) -> redis.Redis:
    
    with open(os.path.dirname(os.path.realpath(__file__)) + CONFIG_FILE) as config:
        settings = json.load(config)

    return redis.Redis(**settings['redis_settings'])