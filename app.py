from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from sqlalchemy import func
from dotenv import load_dotenv
try:
    from bson.objectid import ObjectId
    from pymongo import MongoClient
except Exception:
    # pymongo may not be installed yet; we'll guard usage later
    ObjectId = None
    MongoClient = None

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'template'))

# Configuration
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-please-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Database configuration
database_url = os.getenv('DATABASE_URL')
# Backend selection: allow using TinyDB (JSON) for workspace-visible storage.
# Set DATA_BACKEND=json to use TinyDB. Otherwise if DATABASE_URL starts
# with 'mongodb' we'll use MongoDB, otherwise SQLAlchemy/SQLite.
data_backend = os.getenv('DATA_BACKEND', '').lower()
is_tiny = data_backend == 'json'
is_mongo = bool(database_url and database_url.startswith('mongodb')) and not is_tiny

if is_tiny and TinyDB is not None:
    # Use TinyDB stored in the Flask instance folder so files are visible in VS Code
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except Exception:
        pass
    tiny_path = os.path.join(app.instance_path, 'data.json')
    tinydb = TinyDB(tiny_path)
    users_table = tinydb.table('users')
    expenses_table = tinydb.table('expenses')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
elif is_mongo and MongoClient is not None:
    # Initialize MongoDB client. If the URI does not include a database name
    # (e.g. mongodb://localhost:27017/), default to `expenses_db` so the app
    # still works with Compass and local servers.
    try:
        mongo_client = MongoClient(database_url, serverSelectionTimeoutMS=5000)
        try:
            # Will succeed if URI includes a database name
            mongo_db = mongo_client.get_default_database()
        except Exception:
            # Fallback DB name
            mongo_db = mongo_client['expenses_db']
    except Exception:
        # Final fallback (should be rare) - create client and pick DB
        mongo_client = MongoClient(database_url)
        mongo_db = mongo_client['expenses_db']

    users_collection = mongo_db['users']
    expenses_collection = mongo_db['expenses']
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
else:
    # Default to SQLAlchemy using DATABASE_URL if provided, otherwise a local
    # SQLite file inside the Flask instance folder.
    if database_url and not is_mongo:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        try:
            os.makedirs(app.instance_path, exist_ok=True)
        except Exception:
            pass
        # Use the expenses.db file in the root directory where existing users are stored
        db_path = os.path.join(os.path.dirname(__file__), 'expenses.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Model (SQLAlchemy) - only used when not using MongoDB
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    expenses = db.relationship('Expense', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


# If MongoDB is configured, provide a lightweight adapter User wrapper
if is_mongo:
    class MongoUser(UserMixin):
        def __init__(self, doc):
            self._doc = doc
            self.id = str(doc.get('_id'))
            self.username = doc.get('username')
            self.email = doc.get('email')
            self.password = doc.get('password')

        def get_id(self):
            return self.id

    def mongo_get_user_by_username(username):
        doc = users_collection.find_one({'username': username})
        return MongoUser(doc) if doc else None

    def mongo_get_user_by_email(email):
        doc = users_collection.find_one({'email': email})
        return MongoUser(doc) if doc else None

    def mongo_get_user_by_id(user_id):
        try:
            oid = ObjectId(user_id)
        except Exception:
            return None
        doc = users_collection.find_one({'_id': oid})
        return MongoUser(doc) if doc else None

# TinyDB adapter
if 'users_table' in globals():
    class TinyUser(UserMixin):
        def __init__(self, doc, doc_id):
            self._doc = doc
            self.id = str(doc_id)
            self.username = doc.get('username')
            self.email = doc.get('email')
            self.password = doc.get('password')

        def get_id(self):
            return self.id

    def tiny_get_user_by_username(username):
        q = Query()
        doc = users_table.get(q.username == username)
        if not doc:
            return None
        return TinyUser(doc, doc.doc_id)

    def tiny_get_user_by_email(email):
        q = Query()
        doc = users_table.get(q.email == email)
        if not doc:
            return None
        return TinyUser(doc, doc.doc_id)

    def tiny_get_user_by_id(user_id):
        try:
            did = int(user_id)
        except Exception:
            return None
        doc = users_table.get(doc_id=did)
        if not doc:
            return None
        return TinyUser(doc, doc.doc_id)


@login_manager.user_loader
def load_user(user_id):
    if is_tiny:
        return tiny_get_user_by_id(user_id)
    if is_mongo:
        return mongo_get_user_by_id(user_id)
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None

# Database Model
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.now)
    time = db.Column(db.String(5), nullable=True)  # HH:MM format
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'amount': self.amount,
            'category': self.category,
            'date': self.date.isoformat(),
            'time': self.time or ''
        }

# Create database tables for SQLAlchemy only
if not is_mongo:
    with app.app_context():
        db.create_all()

@app.route("/")
def index():
    if current_user.is_authenticated:
        return render_template("index.html")
    return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        if is_tiny:
            user = tiny_get_user_by_username(username)
            if user and check_password_hash(user.password, password):
                login_user(user)
                return jsonify({"success": True}), 200
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

        if is_mongo:
            user = mongo_get_user_by_username(username)
            if user and check_password_hash(user.password, password):
                login_user(user)
                return jsonify({"success": True}), 200
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

        # SQLAlchemy path
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return jsonify({"success": True}), 200
        return jsonify({"success": False, "message": "Invalid credentials"}), 401
    
    return render_template("login.html")

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if is_tiny:
        q = Query()
        if users_table.get(q.username == username):
            return jsonify({"success": False, "message": "Username already exists"}), 400
        if users_table.get(q.email == email):
            return jsonify({"success": False, "message": "Email already registered"}), 400

        hashed = generate_password_hash(password)
        inserted_id = users_table.insert({
            'username': username,
            'email': email,
            'password': hashed,
            'created_at': datetime.utcnow().isoformat()
        })
        user = tiny_get_user_by_id(str(inserted_id))
        login_user(user)
        return jsonify({"success": True}), 201

    if is_mongo:
        # Check for existing username/email
        if users_collection.find_one({'username': username}):
            return jsonify({"success": False, "message": "Username already exists"}), 400
        if users_collection.find_one({'email': email}):
            return jsonify({"success": False, "message": "Email already registered"}), 400

        hashed = generate_password_hash(password)
        res = users_collection.insert_one({
            'username': username,
            'email': email,
            'password': hashed,
            'created_at': datetime.utcnow()
        })
        user = mongo_get_user_by_id(str(res.inserted_id))
        login_user(user)
        return jsonify({"success": True}), 201

    # SQLAlchemy path
    if User.query.filter_by(username=username).first():
        return jsonify({"success": False, "message": "Username already exists"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already registered"}), 400

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return jsonify({"success": True}), 201

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/api/user")
@login_required
def get_user():
    return jsonify({
        "username": current_user.username,
        "email": current_user.email
    })

@app.route("/api/expenses", methods=["GET"])
@login_required
def get_expenses():
    if is_tiny:
        user_id = int(current_user.get_id())
        docs = expenses_table.search(Query().user_id == user_id)
        # sort by date desc (date stored as ISO string)
        docs_sorted = sorted(docs, key=lambda d: d.get('date', ''), reverse=True)
        results = []
        for d in docs_sorted:
            results.append({
                'id': str(d.doc_id),
                'description': d.get('description'),
                'amount': d.get('amount'),
                'category': d.get('category'),
                'date': d.get('date'),
                'time': d.get('time', '')
            })
        return jsonify(results)

    if is_mongo:
        docs = list(expenses_collection.find({'user_id': ObjectId(current_user.get_id())}).sort('date', -1))
        results = []
        for d in docs:
            results.append({
                'id': str(d.get('_id')),
                'description': d.get('description'),
                'amount': d.get('amount'),
                'category': d.get('category'),
                'date': d.get('date'),
                'time': d.get('time', '')
            })
        return jsonify(results)

    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    return jsonify([exp.to_dict() for exp in expenses])

@app.route("/api/expenses", methods=["POST"])
@login_required
def add_expense():
    data = request.json
    if is_tiny:
        doc = {
            'user_id': int(current_user.get_id()),
            'description': data.get('description'),
            'amount': float(data.get('amount')),
            'category': data.get('category'),
            'date': data.get('date'),
            'time': data.get('time', ''),
            'created_at': datetime.utcnow().isoformat()
        }
        inserted_id = expenses_table.insert(doc)
        return jsonify({
            'id': str(inserted_id),
            'description': doc.get('description'),
            'amount': doc.get('amount'),
            'category': doc.get('category'),
            'date': doc.get('date'),
            'time': doc.get('time', '')
        }), 201

    if is_mongo:
        doc = {
            'user_id': ObjectId(current_user.get_id()),
            'description': data.get('description'),
            'amount': float(data.get('amount')),
            'category': data.get('category'),
            'date': data.get('date'),
            'time': data.get('time', ''),
            'created_at': datetime.utcnow()
        }
        res = expenses_collection.insert_one(doc)
        doc['_id'] = res.inserted_id
        return jsonify({
            'id': str(doc.get('_id')),
            'description': doc.get('description'),
            'amount': doc.get('amount'),
            'category': doc.get('category'),
            'date': doc.get('date'),
            'time': doc.get('time', '')
        }), 201

    expense = Expense(
        user_id=current_user.id,
        description=data.get("description"),
        amount=float(data.get("amount")),
        category=data.get("category"),
        date=datetime.strptime(data.get("date"), '%Y-%m-%d').date(),
        time=data.get("time", "")
    )
    db.session.add(expense)
    db.session.commit()
    return jsonify(expense.to_dict()), 201

@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
@login_required
def delete_expense(expense_id):
    if is_tiny:
        try:
            did = int(expense_id)
        except Exception:
            return jsonify({"success": False}), 400
        doc = expenses_table.get(doc_id=did)
        if doc and doc.get('user_id') == int(current_user.get_id()):
            expenses_table.remove(doc_ids=[did])
        return jsonify({"success": True}), 200

    if is_mongo:
        try:
            oid = ObjectId(expense_id)
        except Exception:
            return jsonify({"success": False}), 400
        expenses_collection.delete_one({'_id': oid, 'user_id': ObjectId(current_user.get_id())})
        return jsonify({"success": True}), 200

    expense = Expense.query.get(expense_id)
    if expense and expense.user_id == current_user.id:
        db.session.delete(expense)
        db.session.commit()
    return jsonify({"success": True}), 200

@app.route("/api/stats", methods=["GET"])
@login_required
def get_stats():
    period = request.args.get('period', 'all')  # all, monthly, weekly, daily
    today = datetime.now().date()
    
    if period == 'daily':
        start_date = today
        end_date = today
    elif period == 'weekly':
        start_date = today - timedelta(days=7)
        end_date = today
    elif period == 'monthly':
        start_date = today - timedelta(days=30)
        end_date = today
    else:  # all
        start_date = None
        end_date = None
    
    # Build query filtered by current user
    if is_tiny:
        user_id = int(current_user.get_id())
        if start_date and end_date:
            docs = expenses_table.search(Query().user_id == user_id)
            expenses = []
            for d in docs:
                d_date = datetime.fromisoformat(d.get('date')).date()
                if d_date >= start_date and d_date <= end_date:
                    expenses.append(d)
        else:
            expenses = expenses_table.search(Query().user_id == user_id)

        total_spent = sum(d.get('amount', 0) for d in expenses)
        week_ago = today - timedelta(days=7)
        weekly_spent = sum(d.get('amount', 0) for d in expenses if datetime.fromisoformat(d.get('date')).date() >= week_ago)
        month_ago = today - timedelta(days=30)
        monthly_spent = sum(d.get('amount', 0) for d in expenses if datetime.fromisoformat(d.get('date')).date() >= month_ago)

        category_data = {}
        for d in expenses:
            cat = d.get('category')
            category_data[cat] = category_data.get(cat, 0) + d.get('amount', 0)
    elif is_mongo:
        # Fetch user's expenses and compute stats in Python
        user_oid = ObjectId(current_user.get_id())
        mongo_filter = {'user_id': user_oid}
        if start_date and end_date:
            docs = list(expenses_collection.find(mongo_filter))
            expenses = []
            for d in docs:
                d_date = datetime.fromisoformat(d.get('date')).date()
                if d_date >= start_date and d_date <= end_date:
                    expenses.append(d)
        else:
            expenses = list(expenses_collection.find(mongo_filter))

        total_spent = sum(d.get('amount', 0) for d in expenses)
        week_ago = today - timedelta(days=7)
        weekly_spent = sum(d.get('amount', 0) for d in expenses if datetime.fromisoformat(d.get('date')).date() >= week_ago)
        month_ago = today - timedelta(days=30)
        monthly_spent = sum(d.get('amount', 0) for d in expenses if datetime.fromisoformat(d.get('date')).date() >= month_ago)

        # Category-wise
        category_data = {}
        for d in expenses:
            cat = d.get('category')
            category_data[cat] = category_data.get(cat, 0) + d.get('amount', 0)
    else:
        base_query = Expense.query.filter_by(user_id=current_user.id)
        
        if start_date and end_date:
            expenses_query = base_query.filter(
                Expense.date >= start_date,
                Expense.date <= end_date
            )
        else:
            expenses_query = base_query
        
        # Total spending
        total_spent = expenses_query.with_entities(func.sum(Expense.amount)).scalar() or 0
        
        # Weekly spending (last 7 days)
        week_ago = today - timedelta(days=7)
        weekly_spent = base_query.filter(
            Expense.date >= week_ago
        ).with_entities(func.sum(Expense.amount)).scalar() or 0
        
        # Monthly spending (last 30 days)
        month_ago = today - timedelta(days=30)
        monthly_spent = base_query.filter(
            Expense.date >= month_ago
        ).with_entities(func.sum(Expense.amount)).scalar() or 0
        
        # Category-wise spending
        category_stats = expenses_query.with_entities(
            Expense.category,
            func.sum(Expense.amount).label('total')
        ).group_by(Expense.category).all()
        
        category_data = {cat: float(total) for cat, total in category_stats}
    
    # Monthly breakdown or Daily breakdown based on period
    if is_tiny:
        if period == 'daily':
            daily_breakdown = {}
            for d in expenses:
                hour = d.get('time', '00').split(':')[0] if d.get('time') else '00'
                key = f"{hour}:00"
                daily_breakdown[key] = daily_breakdown.get(key, 0) + d.get('amount', 0)
            for i in range(24):
                hour = f"{i:02d}:00"
                if hour not in daily_breakdown:
                    daily_breakdown[hour] = 0
            breakdown = dict(sorted(daily_breakdown.items()))
        elif period == 'weekly':
            daily_breakdown = {}
            for i in range(7):
                day = today - timedelta(days=6-i)
                day_name = day.strftime('%a')
                daily_breakdown[day_name] = 0
            for d in expenses:
                day_name = datetime.fromisoformat(d.get('date')).strftime('%a')
                daily_breakdown[day_name] += d.get('amount', 0)
            breakdown = daily_breakdown
        else:
            monthly_breakdown = {}
            for i in range(6):
                month_date = today - timedelta(days=30*i)
                month_key = month_date.strftime('%b %Y')
                month_start = month_date.replace(day=1)
                if i > 0:
                    prev_month = today - timedelta(days=30*(i-1))
                    month_end = prev_month.replace(day=1) - timedelta(days=1)
                else:
                    month_end = today
                amt = 0
                for d in expenses:
                    d_date = datetime.fromisoformat(d.get('date')).date()
                    if d_date >= month_start and d_date <= month_end:
                        amt += d.get('amount', 0)
                monthly_breakdown[month_key] = float(amt)
            breakdown = monthly_breakdown
    elif is_mongo:
        if period == 'daily':
            daily_breakdown = {}
            for d in expenses:
                hour = d.get('time', '00').split(':')[0] if d.get('time') else '00'
                key = f"{hour}:00"
                daily_breakdown[key] = daily_breakdown.get(key, 0) + d.get('amount', 0)
            for i in range(24):
                hour = f"{i:02d}:00"
                if hour not in daily_breakdown:
                    daily_breakdown[hour] = 0
            breakdown = dict(sorted(daily_breakdown.items()))
        elif period == 'weekly':
            daily_breakdown = {}
            for i in range(7):
                day = today - timedelta(days=6-i)
                day_name = day.strftime('%a')
                daily_breakdown[day_name] = 0
            for d in expenses:
                day_name = datetime.fromisoformat(d.get('date')).strftime('%a')
                daily_breakdown[day_name] += d.get('amount', 0)
            breakdown = daily_breakdown
        else:
            monthly_breakdown = {}
            for i in range(6):
                month_date = today - timedelta(days=30*i)
                month_key = month_date.strftime('%b %Y')
                month_start = month_date.replace(day=1)
                if i > 0:
                    prev_month = today - timedelta(days=30*(i-1))
                    month_end = prev_month.replace(day=1) - timedelta(days=1)
                else:
                    month_end = today
                amt = 0
                for d in expenses:
                    d_date = datetime.fromisoformat(d.get('date')).date()
                    if d_date >= month_start and d_date <= month_end:
                        amt += d.get('amount', 0)
                monthly_breakdown[month_key] = float(amt)
            breakdown = monthly_breakdown
    else:
        if period == 'daily':
            # Show hourly breakdown for today
            daily_breakdown = {}
            for exp in expenses_query.all():
                hour = exp.time.split(':')[0] if exp.time else '00'
                key = f"{hour}:00"
                daily_breakdown[key] = daily_breakdown.get(key, 0) + exp.amount
            # Fill missing hours
            for i in range(24):
                hour = f"{i:02d}:00"
                if hour not in daily_breakdown:
                    daily_breakdown[hour] = 0
            breakdown = dict(sorted(daily_breakdown.items()))
        elif period == 'weekly':
            # Show daily breakdown for this week
            daily_breakdown = {}
            for i in range(7):
                day = today - timedelta(days=6-i)
                day_name = day.strftime('%a')
                daily_breakdown[day_name] = 0
            for exp in expenses_query.all():
                day_name = exp.date.strftime('%a')
                daily_breakdown[day_name] += exp.amount
            breakdown = daily_breakdown
        else:
            # Monthly breakdown (last 6 months or filtered month)
            monthly_breakdown = {}
            for i in range(6):
                month_date = today - timedelta(days=30*i)
                month_key = month_date.strftime('%b %Y')
                month_start = month_date.replace(day=1)
                if i > 0:
                    prev_month = today - timedelta(days=30*(i-1))
                    month_end = prev_month.replace(day=1) - timedelta(days=1)
                else:
                    month_end = today
                
                amount = Expense.query.filter(
                    Expense.date >= month_start,
                    Expense.date <= month_end
                ).with_entities(func.sum(Expense.amount)).scalar() or 0
                monthly_breakdown[month_key] = float(amount)
            breakdown = monthly_breakdown
    
    return jsonify({
        'total_spent': float(total_spent),
        'weekly_spent': float(weekly_spent),
        'monthly_spent': float(monthly_spent),
        'category_stats': category_data,
        'breakdown': breakdown,
        'period': period
    })

if __name__ == "__main__":
    debug_mode = os.getenv('FLASK_ENV', 'production') == 'development'
    port = int(os.getenv('PORT', 4048))
    app.run(debug=debug_mode, port=port, host='0.0.0.0')
    