import logging
from typing import Any
from pydantic import BaseModel
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)

DYNAMO_TABLE = "website-table"

class Track(BaseModel):
    disc: str
    track_id: int
    title: str
    duration: str
    
class VGMInfo(BaseModel):
    rating: int 
    description: str | None = None
    extras: list[dict | str] | None = None
    
class VGMEntry(VGMInfo):
    year_listened: int
    catalog_num: str 
    game: str
    img: str | None = None
    tracks: list[Track] | None = None
    
    #DynamoDB Specific Functions
    
    def get_dynamo_formatted_dict(self) -> dict[str, str]:
        data_dict = self.model_dump()
        item_dict = {
            'pk':f'{data_dict.pop("year_listened")}',
            'sk':f'{"game"}|{data_dict.pop("game")}',
            'gsi_sk':f'{"game"}|{getattr(self,"game")}',
        }
        return {**item_dict,**data_dict}
    
    
    def get_dynamo_pksk(self) -> dict[str, str]:
        item_dict = {
            'pk':f'{getattr(self,"year_listened")}',
            'sk':f'{"game"}|{getattr(self,"game")}',
        }
        return item_dict
    
    def get_dynamo_update_item_config(self) -> dict[str, Any]:
        config = {
            "Key":self.get_dynamo_pksk(), 
            "UpdateExpression":"set gsi_sk=:sk, genre=:g, img=:i, catalog_num=:c, rating=:r, description=:d",
            "ExpressionAttributeValues":{ 
                ":sk":f'{"game"}|{getattr(self,"game")}',
                ":i":self.img, 
                ":c":self.catalog_num, 
                ":r":self.rating, 
                ":d":self.description
            },
            "ReturnValues":"ALL_NEW",
        }
        return config
    
    @staticmethod
    def convert_pksk_to_real_vals(data: dict) -> dict:
        new_data = data
        try:
            new_data['year_listened'] = new_data.pop('pk')
            new_data['game'] = new_data.pop('sk').lstrip(f'{VGMEntry.get_sk_prefix()}|')
        except Exception:
            logger.exception("Error in convert_pksk_to_real_vals")
            return data
        else:
            return new_data
    
    @staticmethod
    def get_sk_prefix():
        return "game"
    ########## END DynamoDB Specific Functions ##########
    
class DynamoDBVGM:
    
    def __init__(self, engine: Any=boto3.resource('dynamodb', region_name="us-east-1"), table_name: str=None, debug: bool=False) -> None:
        self.engine = engine
        self.table_name = table_name
        self._exists = None
        
        if self.table_exists:
            self.table = self.engine.Table(self.table_name)
        else:
            logger.info("Created DynamoDB table %s", self.table_name)
            self.table = self._create_table()

        if debug:
            self.debug()
        
    @property
    def table_exists(self) -> bool:
        if self._exists is None:
            try:
                test_table = self.engine.Table(self.table_name)
                test_table.load()
                self._exists = True
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    self._exists = False
                else:
                    logging.exception("Table existence checker failed in DynamoDBVGM")
                    raise e
            test_table = None
        return self._exists
        
    def _create_table(self):
        try:
            new_table = self.engine.create_table(
                TableName = self.table_name,
                KeySchema=[
                    {'AttributeName':'pk', 'KeyType': 'HASH'},
                    {'AttributeName':'sk', 'KeyType': 'RANGE'},
                ],
                AttributeDefinitions=[
                    {'AttributeName':'pk', 'AttributeType':'S'},
                    {'AttributeName':'sk', 'AttributeType':'S'},
                    {'AttributeName':'gsi_sk', 'AttributeType':'S'},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName":'gsiIndex',
                        "KeySchema": [
                            {"AttributeName": "gsi_sk", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                        "ProvisionedThroughput":{
                            'ReadCapacityUnits':5,
                            'WriteCapacityUnits':5,  
                        },
                    },
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits':5,
                    'WriteCapacityUnits':5,  
                },
            )
            new_table.wait_until_exists()
        except ClientError as e:
            #TODO: Logging
            raise e
        else:
            return new_table
        
    def delete_table(self) -> None:
        try:
            self.table.delete()
            self.table = None
            self._exists = False
        except ClientError as e:
            raise e
        
    def debug(self) -> None:
        logger.info(f"Debug mode ON for class: {self.__class__}")
        #TODO: debug functions?
        
    def add(self, data: VGMEntry) -> VGMEntry:
        try:
            self.table.put_item(Item=data.get_dynamo_formatted_dict())
        except ClientError as e:
            #TODO: Logging
            raise e
        else:
            return data
        
    def update(self, data: VGMEntry) -> VGMEntry:
        #TODO: Get the item and only update the passed kwargs
        try:
            self.table.update_item(**data.get_dynamo_update_item_config())
        except ClientError as e:
            raise e
        else:
            return data

        
    def delete(self, data: VGMEntry) -> dict[str, Any]:
        try:
            response = self.table.delete_item(Key=data.get_dynamo_pksk(), ReturnValues="ALL_OLD")
                
        except ClientError as e:
            #TODO: Logging and error coverage
            raise e
        else:
            if response.get('Attributes', None):
                return data
            else:
                return {}
    
    def query_year(self, year:str) -> list[dict[str, Any]]:
        try:
            response = self.table.query(
                Select='SPECIFIC_ATTRIBUTES',
                ProjectionExpression="catalog_num, description, genre, img, pk, rating, sk",
                KeyConditionExpression=Key('pk').eq(year) & Key('sk').begins_with(VGMEntry.get_sk_prefix()),
            )
        except:
            raise
        
        else:
            try:
                if "Items" in response:
                    data = [VGMEntry(**VGMEntry.convert_pksk_to_real_vals(item)) for item in response["Items"]]
                else:
                    data = []
            except (IndexError, KeyError):
                return []
            else:
                return data
        
    def query_game(self, game:str) -> dict[str, Any]:
        try:
            response = self.table.query(
                Select='SPECIFIC_ATTRIBUTES', 
                ProjectionExpression="catalog_num, description, genre, img, pk, rating, sk, tracks",
                IndexName='gsiIndex', 
                KeyConditionExpression=Key('gsi_sk').eq(f'{VGMEntry.get_sk_prefix()}|{game}'),
            )
        except:
            raise
        else:
            try:
                if "Items" in response:
                    myup = str(response)
                    logger.info("Test: %s", myup)
                    data = VGMEntry(**VGMEntry.convert_pksk_to_real_vals(response["Items"][0]))
                else:
                    return {}
            except (IndexError, KeyError):
                return {}
            else:
                return data
        
def get_vgmdb():
    return DynamoDBVGM(table_name=DYNAMO_TABLE)