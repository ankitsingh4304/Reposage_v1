import os

from pymongo import MongoClient

MONGO_URI = os.environ["MONGO_URI"]

client = MongoClient(MONGO_URI)
db = client.get_database("reposage")

def get_db():
    return db
