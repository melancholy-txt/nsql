import uuid
import pymongo
from werkzeug.security import generate_password_hash
from datetime import datetime

mongo_client = pymongo.MongoClient("mongodb://admin:admin@mongodb:27017/")  
db = mongo_client["reviews_db"]
reviews_collection = db["reviews_collection"]
users_collection = db["users_collection"]
comments_collection = db["comments_collection"]

# Create admin user if not exists
if not users_collection.find_one({"username": "admin"}):
    admin_user = {
        "username": "admin",
        "password_hash": generate_password_hash("admin123"),
        "is_admin": True,
        "created_at": datetime.now()
    }
    users_collection.insert_one(admin_user)
    print("Admin user created (username: admin, password: admin123)")

recenze = [
    {
        "id": str(uuid.uuid4()),
        "nazev": "The Witcher 3: Wild Hunt",
        "zanr": "RPG",
        "hodnoceni": 10,
        "recenze": "Jedna z nejlepších her všech dob. Skvělý příběh, úžasný svět a propracovaní hrdinové."
    },
    {
        "id": str(uuid.uuid4()),
        "nazev": "Cyberpunk 2077",
        "zanr": "Action RPG",
        "hodnoceni": 8,
        "recenze": "Po všech patchích skvělá hra s fascinujícím světem a epickým příběhem."
    },
    {
        "id": str(uuid.uuid4()),
        "nazev": "Elden Ring",
        "zanr": "Action RPG",
        "hodnoceni": 9,
        "recenze": "Mistrovské dílo od FromSoftware. Náročné, ale spravedlivé a neuvěřitelně uspokojivé."
    },
    {
        "id": str(uuid.uuid4()),
        "nazev": "Stardew Valley",
        "zanr": "Simulace",
        "hodnoceni": 9,
        "recenze": "Relaxační farmářská hra plná obsahu. Perfektní na odpočinek po náročném dni."
    }
]

if reviews_collection.count_documents({}) == 0:
    inserted = reviews_collection.insert_many(recenze)
    review_ids = [str(_id) for _id in inserted.inserted_ids]
    print("Initial reviews loaded!")
else:
    existing_reviews = list(reviews_collection.find().limit(4))
    review_ids = [str(review["_id"]) for review in existing_reviews]
    print("Reviews already exist, skipping insert.")

sample_users = [
    {"username": "eva", "password": "eva123"},
    {"username": "petr", "password": "petr123"},
    {"username": "jana", "password": "jana123"}
]

for user in sample_users:
    if not users_collection.find_one({"username": user["username"]}):
        users_collection.insert_one({
            "username": user["username"],
            "password_hash": generate_password_hash(user["password"]),
            "is_admin": False,
            "created_at": datetime.now()
        })

if comments_collection.count_documents({}) == 0 and review_ids:
    sample_comments = [
        {
            "review_id": review_ids[0],
            "author": "eva",
            "text": "Skvela hra, stravil jsem u ni desitky hodin.",
            "created_at": datetime.now()
        },
        {
            "review_id": review_ids[0],
            "author": "petr",
            "text": "Pribeh je top, ale bojovy system mi nesedl.",
            "created_at": datetime.now()
        },
        {
            "review_id": review_ids[1] if len(review_ids) > 1 else review_ids[0],
            "author": "jana",
            "text": "Po patchich se to hraje fakt dobre.",
            "created_at": datetime.now()
        }
    ]
    comments_collection.insert_many(sample_comments)
    print("Sample comments loaded!")
else:
    print("Comments already exist, skipping insert.")