import uuid
import pymongo

mongo_client = pymongo.MongoClient("mongodb://admin:admin@mongodb:27017/")  
db = mongo_client["reviews_db"]
reviews_collection = db["reviews_collection"]

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

reviews_collection.insert_many(recenze)
print("Initial data loaded!")