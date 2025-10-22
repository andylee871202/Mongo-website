import pandas as pd
import json
import pymongo
import configparser

config = configparser.ConfigParser()
config.read('/app/config.env')

def get_root_mongodb_url():
    user = config['MongoDB']['MONGO_ROOT_USERNAME']
    pwd = config['MongoDB']['MONGO_ROOT_PASSWORD']
    host = config['MongoDB']['MONGO_HOST']
    port = config['MongoDB']['MONGO_PORT']
    database = config['MongoDB']['MONGO_DATABASE']

    return f"mongodb://{user}:{pwd}@{host}:{port}/?authSource=admin"

def create_database():
    database = config['MongoDB']['MONGO_DATABASE']
    url = get_root_mongodb_url()
    client = pymongo.MongoClient(url)
    db = client[database]

    poem_collection = db['poem']
    poem_collection.create_index('ID', unique=True)
    poem_collection.create_index('title', unique=False)
    poem_collection.create_index('form', unique=False)
    poem_collection.create_index('era', unique=False)
    poem_collection.create_index('author', unique=False)
    poem_collection.create_index('content_raw', unique=False)
    poem_collection.create_index('content_norm', unique=False)
    poem_collection.create_index('search_text', unique=False)
    poem_collection.create_index('ngrams_bi', unique=False)
    poem_collection.create_index('meta', unique=False)
    poem_collection.create_index('created_date', unique=False)
    poem_collection.create_index('updated_date', unique=False)

    client.close()
    return True

if __name__ == '__main__':
    create_database()
    
    


