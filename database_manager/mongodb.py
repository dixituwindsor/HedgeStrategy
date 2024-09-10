import os
from pymongo import MongoClient
from dotenv import load_dotenv
from threading import Lock


# Singleton Class
class MongoDB:
    __instance = None
    __lock = Lock()

    # Get Instance of the MongoDb Class
    @classmethod
    def getInstance(cls):
        if not cls.__instance:
            with cls.__lock:
                if not cls.__instance:
                    cls.__instance = cls()

        return cls.__instance

    def __init__(self):
        if MongoDB.__instance is None:
            MongoDB.__instance = self
            load_dotenv()
            self.client = MongoClient(os.getenv('MONGO_DB_URI'))
            self.db_list = self.client.list_database_names()

            # Check if DB_Name if Exist in DataBase or not
            if os.getenv('MONGO_DB_NAME') not in self.db_list:
                self.db = self.client[os.getenv('MONGO_DB_NAME')]
            else:
                self.db = self.client.get_database(os.getenv('MONGO_DB_NAME'))
        else:
            raise Exception("You can not Create Another Instance of MongoDB Class. MongoDB Class is Singleton Class")

    def isCollectionExists(self, collection_name):
        collections = self.db.list_collection_names()
        return True if collection_name.lower() in collections else False

    def createCollection(self, collection_name):
        """Function to Create New Collection in DataBase"""
        if not self.isCollectionExists(collection_name=collection_name):
            self.db.create_collection(name=collection_name)
            return self.db[collection_name]
        return None

    def dropCollection(self, collection_name):
        collection = self.db[collection_name]
        collection.drop()

    def insertOne(self, collection_name: str, data: dict):
        return self.db[collection_name].insert_one(data)

    def insertMany(self, collection_name: str, data: list, drop_collection: bool = False):
        if drop_collection:
            self.dropCollection(collection_name)

        return self.db[collection_name].insert_many(data)

    def findOne(self, collection_name, find_filter=None, value_filter=None):
        if value_filter is None:
            value_filter = {}
        if find_filter is None:
            find_filter = {}
        return self.db[collection_name].find_one(find_filter, value_filter)

    def findMany(self, collection_name, find_filter=None, value_filter=None):
        if value_filter is None:
            value_filter = {}
        if find_filter is None:
            find_filter = {}
        results = self.db[collection_name].find(find_filter, value_filter)
        return results

    def updateOne(self, collection_name, update_filter, update_value):
        update_data = self.db[collection_name].update_one(update_filter, {'$set': update_value}, upsert=True)
        return update_data

    def updateMany(self, collection_name, update_filter, update_value):
        update_data = self.db[collection_name].update_many(update_filter, {'$set': update_value}, upsert=True)
        return update_data

    def deleteOne(self, collection_name, find_filter):
        deleted = self.db[collection_name].delete_one(find_filter)
        return deleted

    def deleteMany(self, collection_name, find_filter):
        deleted = self.db[collection_name].delete_many(find_filter)
        return deleted


if __name__ == '__main__':
    mongo = MongoDB()
