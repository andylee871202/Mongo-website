import pandas as pd
import json
import pymongo
import configparser

config = configparser.ConfigParser()
config.read('/app/config.env')

def get_root_mongodb_url():
    root_username = config['MongoDB']['MONGO_ROOT_USERNAME']
    root_password = config['MongoDB']['MONGO_ROOT_PASSWORD']
    host = config['MongoDB']['MONGO_HOST']
    port = config['MongoDB']['MONGO_PORT']
    database = config['MongoDB']['MONGO_DATABASE']

    return f"mongodb://{root_username}:{root_password}@{host}:{port}/{database}?authSource=admin"

def create_database():
    database = config['MongoDB']['MONGO_DATABASE']
    url = get_root_mongodb_url()
    client = pymongo.MongoClient(url)
    db = client[database]

    poem_collection = db['poem']
    poem_collection.create_index([('ID', pymongo.ASCENDING)], unique=True)
    poem_collection.create_index([('title', pymongo.ASCENDING)])
    poem_collection.create_index([('form', pymongo.ASCENDING)])
    poem_collection.create_index([('era', pymongo.ASCENDING)])
    poem_collection.create_index([('author', pymongo.ASCENDING)])
    poem_collection.create_index([('content_raw', pymongo.ASCENDING)], unique=True)
    poem_collection.create_index([('content_norm', pymongo.ASCENDING)])
    poem_collection.create_index([('search_text', pymongo.ASCENDING)])
    poem_collection.create_index([('ngrams_bi', pymongo.ASCENDING)])
    poem_collection.create_index([('meta', pymongo.ASCENDING)])
    poem_collection.create_index([('created_date', pymongo.ASCENDING)])
    poem_collection.create_index([('updated_date', pymongo.ASCENDING)])

    client.close()
    return True

if __name__ == '__main__':
    create_database()
    
    


