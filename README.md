# 💰 Expense Tracker

A modern, full-stack expense tracking application with user authentication, real-time charts, and comprehensive spending analytics.

## Features

✅ **User Authentication**
- Register new accounts
- Secure login with password hashing
- Session management

✅ **Expense Management**
- Add expenses with description, amount, category, date, and time
- Delete expenses
- View full spending history

✅ **Advanced Dashboard**
- Real-time spending statistics
- Interactive charts (pie charts & line/bar graphs)
- Filter by period: All Time, Monthly, Weekly, Daily
- Category-wise spending breakdown
- Monthly spending trends

✅ **Dark Theme UI**
- Modern dark blue/black interface
- Cyan and lime green accents
- Fully responsive design
- Smooth animations

## Tech Stack

**Backend:**
- Flask (Python web framework)
- Flask-SQLAlchemy (ORM)
- Flask-Login (Authentication)
- Werkzeug (Password hashing)

**Frontend:**
- HTML5
- CSS3 (Custom styling)
- JavaScript (Vanilla, no frameworks)
- Chart.js (Data visualization)

**Database:**
- SQLite (Development)
- PostgreSQL/MySQL (Production ready)

## Installation

### 1. Clone/Setup the Project
```bash
cd Expense_tracker
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv env
env\Scripts\activate

# macOS/Linux
python3 -m venv env
source env/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install gunicorn  # For production
```

### 4. Setup Environment Variables
```bash
# Copy the example file
cp .env.example .env

# Edit .env and set your values
# Minimum required: SECRET_KEY
```

### 5. Run the Application
```bash
# Development mode
python app.py

# Visit: http://localhost:4048
```

## Deployment

### Local/Development
```bash
python app.py
```

### Heroku Deployment
```bash
# 1. Install Heroku CLI
# 2. Login to Heroku
heroku login

# 3. Create a new app
heroku create your-app-name

# 4. Set environment variables
heroku config:set SECRET_KEY="your-random-secret-key"
heroku config:set FLASK_ENV="production"

# 5. Add PostgreSQL addon
heroku addons:create heroku-postgresql:hobby-dev

# 6. Deploy
git push heroku main
```

### PythonAnywhere Deployment
1. Sign up at pythonanywhere.com
2. Upload your files
3. Create a new web app
4. Configure WSGI file
5. Set environment variables in the web app settings
6. Reload the app

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install gunicorn

COPY . .

ENV FLASK_ENV=production
EXPOSE 4048

CMD ["gunicorn", "--bind", "0.0.0.0:4048", "app:app"]
```

## Project Structure
```
Expense_tracker/
├── app.py                   # Main Flask application
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
├── Procfile                # Heroku deployment
├── expenses.db             # SQLite database (created on first run)
└── template/
    ├── login.html          # Login/Register page
    └── index.html          # Main dashboard
```

## Environment Variables

**Required:**
- `SECRET_KEY` - Flask session secret (use a long random string for production)

**Optional:**
- `FLASK_ENV` - Set to "development" or "production" (default: production)
- `DATABASE_URL` - Full database connection string (uses SQLite if not set)
- `PORT` - Port to run on (default: 4048)
- `SESSION_COOKIE_SECURE` - Set to "True" for HTTPS only (default: False)

## Database Schema

### Users Table
```
- id (Primary Key)
- username (Unique)
- email (Unique)
- password (Hashed)
- created_at
```

### Expenses Table
```
- id (Primary Key)
- user_id (Foreign Key → Users)
- description
- amount
- category
- date
- time (Optional)
- created_at
```

## Usage

### 1. Register an Account
- Click "Register" tab
- Enter username, email, password
- Submit

### 2. Login
- Enter your credentials
- Click "Login"

### 3. Add Expenses
- Click "➕ Add Expense" tab
- Fill in details (description, amount, category, date, optional time)
- Click "Add Expense"

### 4. View Dashboard
- Click "📊 Dashboard" tab
- Filter by: All Time, Monthly, Weekly, Daily
- View charts and statistics

### 5. View History
- Click "📋 History" tab
- Search by description
- Filter by category
- View all expenses
- Delete individual expenses

## API Endpoints

### Authentication
- `POST /login` - Login user
- `POST /register` - Register new user
- `GET /logout` - Logout user

### Expenses
- `GET /api/expenses` - Get all expenses (user-specific)
- `POST /api/expenses` - Add new expense
- `DELETE /api/expenses/<id>` - Delete expense
- `GET /api/stats?period=all|monthly|weekly|daily` - Get spending statistics
- `GET /api/user` - Get current user info

## Security Notes

⚠️ **Important for Production:**
1. Change the `SECRET_KEY` to a long random string
2. Set `FLASK_ENV=production`
3. Set `SESSION_COOKIE_SECURE=True` if using HTTPS
4. Use a production database (PostgreSQL recommended)
5. Enable HTTPS
6. Use environment variables (never commit .env file)
7. Add `.env` to `.gitignore`

## Future Enhancements

- [ ] Email verification
- [ ] Password reset functionality
- [ ] Budget planning
- [ ] Recurring expenses
- [ ] Export to CSV/PDF
- [ ] Mobile app
- [ ] Multi-currency support
- [ ] Savings goals

## License

MIT License

## Support

For issues or questions, please create an issue in the repository.

---

**Ready for Production!** ✅
