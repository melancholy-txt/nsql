import time
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, abort, flash, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
import redis
import uuid
import pymongo
from bson.objectid import ObjectId
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# Configure Flask-Session with Redis
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.Redis(host='redis', port=6379)
Session(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Pro tuto akci se musíte přihlásit.'

mongo_client = pymongo.MongoClient("mongodb://admin:admin@mongodb:27017/")  
db = mongo_client["reviews_db"]
reviews_collection = db["reviews_collection"]
comments_collection = db["comments_collection"]
users_collection = db["users_collection"]

# Enable automatic decoding of responses
r = redis.Redis(host='redis', port=6379, decode_responses=True)


class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.is_admin = user_data.get('is_admin', False)


@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = users_collection.find_one({"_id": ObjectId(user_id)})
        if user_data:
            print(f"Loading user: {user_id} -> {user_data}")
            return User(user_data)
    except:
        pass
    return None


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


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

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect("/")
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user_data = users_collection.find_one({"username": username})
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data)
            login_user(user)
            flash('Přihlášení úspěšné!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or "/")
        else:
            flash('Nesprávné uživatelské jméno nebo heslo.', 'error')
    
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('Odhlášení úspěšné.', 'success')
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect("/")
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirm")
        
        if not username or not password:
            flash('Vyplňte všechna pole.', 'error')
            return render_template("register.html")
        
        if password != password_confirm:
            flash('Hesla se neshodují.', 'error')
            return render_template("register.html")
        
        if users_collection.find_one({"username": username}):
            flash('Uživatelské jméno již existuje.', 'error')
            return render_template("register.html")
        
        new_user = {
            "username": username,
            "password_hash": generate_password_hash(password),
            "is_admin": False,
            "created_at": datetime.now()
        }
        users_collection.insert_one(new_user)
        flash('Registrace úspěšná! Nyní se můžete přihlásit.', 'success')
        return redirect("/login")
    
    return render_template("register.html")

@app.route("/")
@app.route("/home")
def zobraz_home():
    return render_template("home.html")

@app.route("/recenze")
def zobraz_recenze():
    # Try to get cached data
    cached_data = r.get("data:reviews")
    
    if cached_data:
        app.logger.info("Reviews data loaded from cache")
        all_reviews = json.loads(cached_data)
    else:
        app.logger.info("Reviews data fetched from MongoDB")
        all_reviews = list(reviews_collection.find())
        for review in all_reviews:
            review['review'] = str(review['_id'])
            review['_id'] = str(review['_id'])
        # Cache data for 5 minutes
        r.setex("data:reviews", 300, json.dumps(all_reviews))
    
    return render_template("recenze.html", data=all_reviews)

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
@login_required
def pridat_komentar(review_id):
    try:
        review = reviews_collection.find_one({"_id": ObjectId(review_id)})
    except:
        abort(404)
    
    if not review:
        abort(404)
    
    new_comment = {
        "review_id": review_id,
        "author": current_user.username,
        "text": request.form["text"],
        "created_at": datetime.now()
    }
    comments_collection.insert_one(new_comment)
    
    return redirect(f"/recenze/{review_id}")

@app.route("/pridat", methods=["GET", "POST"])
@admin_required
def pridat_recenzi():
    if request.method == "GET":
        return render_template("pridat.html")
    elif request.method == "POST":
        nova_recenze = {
            "id": str(uuid.uuid4()),
            "nazev": request.form["nazev"],
            "zanr": request.form["zanr"],
            "hodnoceni": request.form["hodnoceni"],
            "recenze": request.form["recenze"]
        }
        reviews_collection.insert_one(nova_recenze)
        
        # Invalidate cache
        r.delete("data:reviews")
        
        return redirect("/recenze")

@app.route("/wipe")
@admin_required
def wipe_recenze():
    reviews_collection.delete_many({})
    # Invalidate cache
    r.delete("data:reviews")
    return "Recenze byly vymazány :("

@app.route("/testcache")
def test_with_cache():
    times = []
    for i in range(10):
        start = time.time()
        cached_data = r.get("data:reviews")
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