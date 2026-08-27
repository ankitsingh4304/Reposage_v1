from pymongo import MongoClient

MONGO_URI = "mongodb+srv://singhankit16220_db_user:4RcbIwugK0fsKrZr@cluster0.s8rpbqj.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client.get_database("reposage")

def get_db():
    return db
