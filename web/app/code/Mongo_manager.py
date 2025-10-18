import pymongo
import configparser
import datetime

config = configparser.ConfigParser()
config.read('/app/config.env')

class MongoManager:
    def __init__(self):
        self.url = get_root_mongodb_url()
        self.client = pymongo.MongoClient(self.url)
        self.db = self.client[config['MongoDB']['MONGO_DATABASE']]
        self.poem_collection = self.db['poem']

    def _get_root_mongodb_url(self):
        root_username = config['MongoDB']['MONGO_ROOT_USERNAME']
        root_password = config['MongoDB']['MONGO_ROOT_PASSWORD']
        host = config['MongoDB']['MONGO_HOST']
        port = config['MongoDB']['MONGO_PORT']
        database = config['MongoDB']['MONGO_DATABASE']

        return f"mongodb://{root_username}:{root_password}@{host}:{port}/{database}?authSource=admin"

    def close(self):
        self.client.close()

    def insert_poem(self, ID, title, form, era, author, content_raw, content_norm, search_text, ngrams_bi, meta):
        created_date = datetime.datetime.now()
        updated_date = datetime.datetime.now()

        try:
            self.poem_collection.insert_one({
                'ID': ID,
                'title': title,
                'form': form,
                'era': era,
                'author': author,
                'content_raw': content_raw,
                'content_norm': content_norm,
                'search_text': search_text,
                'ngrams_bi': ngrams_bi,
                'meta': meta,
                'created_date': created_date,
                'updated_date': updated_date
            })
            return True
        except Exception as e:
            raise Exception(f"Error inserting poem: {e}")
            return False

    def del_poem(self, ID):
        try:
            self.poem_collection.delete_one({
                'ID': ID
            })
        except Exception as e:
            raise Exception(f"Error deleting poem: {e}")

    def get_poem(self, ID):
        try:
            return self.poem_collection.find_one({
                'ID': ID
            })
        except Exception as e:
            raise Exception(f"Error getting poem: {e}")
    
    def update_poem(self, update_dic):
        update_date = datetime.datetime.now()
        try:
            self.poem_collection.update_one({
                'ID': update_dic['ID']
            }, {
                '$set': update_dic
            })
        except Exception as e:
            raise Exception(f"Error updating poem: {e}")

    def search_by_title(self, title):
        try:
            return self.poem_collection.find({
                'title': title
            })
        except Exception as e:
            raise Exception(f"Error searching by title: {e}")
    
    def search_by_author(self, author):
        try:
            return self.poem_collection.find({
                'author': author
            })
        except Exception as e:
            raise Exception(f"Error searching by author: {e}")
    
    def search_by_form(self, form):
        try:
            return self.poem_collection.find({
                'form': form
            })
        except Exception as e:
            raise Exception(f"Error searching by form: {e}")