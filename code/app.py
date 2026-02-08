import time
from datetime import datetime
from flask import Flask, render_template, request, redirect, abort
import redis
import uuid
import pymongo
from bson.objectid import ObjectId
import json

app = Flask(__name__)

mongo_client = pymongo.MongoClient("mongodb://admin:admin@mongodb:27017/")  
db = mongo_client["reviews_db"]
reviews_collection = db["reviews_collection"]
comments_collection = db["comments_collection"]

# Enable automatic decoding of responses
r = redis.Redis(host='redis', port=6379, decode_responses=True)


def get_cached_page(cache_key, expire_time, render_func):
    """Get cached page or render and cache it"""
    cached_page = r.get(cache_key)
    
    if cached_page:
        app.logger.info(f"Page {cache_key} loaded from cache")
        return cached_page
    
    # Render the page
    response = render_func()
    
    # Cache the rendered HTML
    r.setex(cache_key, expire_time, response)
    app.logger.info(f"Page {cache_key} rendered and cached")
    
    return response

@app.route("/")
@app.route("/home")
def zobraz_home():
    return get_cached_page(
        "page:home",
        600,
        lambda: render_template("home.html")
    )

@app.route("/recenze")
def zobraz_recenze():
    start_time = time.time()
    
    def render_page():
        all_reviews = list(reviews_collection.find())
        for review in all_reviews:
            review['review'] = str(review['_id'])
            review['_id'] = str(review['_id'])
        return render_template("recenze.html", data=all_reviews)
    
    response = get_cached_page("page:recenze", 300, render_page)
    
    load_time = time.time() - start_time
    app.logger.info(f"Recenze page loaded in {load_time*1000:.2f}ms")
    
    return response

@app.route("/recenze/<review_id>")
def zobraz_recenzi_detail(review_id):
    try:
        review = reviews_collection.find_one({"_id": ObjectId(review_id)})
    except:
        abort(404)
    
    if not review:
        abort(404)
    
    review['_id'] = str(review['_id'])
    
    # Get comments for this review
    comments = list(comments_collection.find({"review_id": review_id}).sort("created_at", -1))
    for comment in comments:
        comment['_id'] = str(comment['_id'])
    
    return render_template("recenze_detail.html", recenze=review, comments=comments)

@app.route("/recenze/<review_id>/comment", methods=["POST"])
def pridat_komentar(review_id):
    try:
        review = reviews_collection.find_one({"_id": ObjectId(review_id)})
    except:
        abort(404)
    
    if not review:
        abort(404)
    
    
    new_comment = {
        "review_id": review_id,
        "author": request.form.get("author", "Anonym"),
        "text": request.form["text"],
        "created_at": datetime.now()
    }
    comments_collection.insert_one(new_comment)
    
    return redirect(f"/recenze/{review_id}")

@app.route("/pridat", methods=["GET", "POST"])
def pridat_recenzi():
    if request.method == "GET":
        return get_cached_page(
            "page:pridat",
            600,
            lambda: render_template("pridat.html")
        )
    elif request.method == "POST":
        nova_recenze = {
            "id": str(uuid.uuid4()),
            "nazev": request.form["nazev"],
            "zanr": request.form["zanr"],
            "hodnoceni": request.form["hodnoceni"],
            "recenze": request.form["recenze"]
        }
        reviews_collection.insert_one(nova_recenze)
        
        # Invalidate caches
        r.delete("page:recenze")
        r.delete("reviews_cache")
        
        return redirect("/recenze")

@app.route("/wipe")
def wipe_recenze():
    reviews_collection.delete_many({})
    # Invalidate cache
    r.delete("reviews_cache")
    return "Recenze byly vymazány :("

@app.route("/testcache")
def test_with_cache():
    times = []
    for i in range(10):
        start = time.time()
        cached_data = r.get("reviews_cache")
        if cached_data:
            json.loads(cached_data)
        elapsed = time.time() - start
        times.append(elapsed * 1000)
    
    avg_time = sum(times) / len(times)
    return f"Average time WITH Redis cache: {avg_time:.2f}ms"

@app.route("/test")
def test_without_cache():
    times = []
    for i in range(10):
        start = time.time()
        all_reviews = list(reviews_collection.find())
        elapsed = time.time() - start
        times.append(elapsed * 1000)
    
    avg_time = sum(times) / len(times)
    return f"Average time WITHOUT Redis cache: {avg_time:.2f}ms"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)