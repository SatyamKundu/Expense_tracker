from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from sqlalchemy import func
from dotenv import load_dotenv

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
if database_url:
    # Production database (PostgreSQL, MySQL, etc.)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Local SQLite database
    db_path = os.path.join(os.path.dirname(__file__), 'expenses.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Model
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

# Create database tables
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
        user = User.query.filter_by(username=data.get("username")).first()
        
        if user and user.check_password(data.get("password")):
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
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    return jsonify([exp.to_dict() for exp in expenses])

@app.route("/api/expenses", methods=["POST"])
@login_required
def add_expense():
    data = request.json
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
    