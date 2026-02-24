# Expense Tracker - Render Deployment Guide

## Overview
This Expense Tracker application is ready for deployment on Render. It supports multiple database backends: PostgreSQL, MongoDB, SQLite, and TinyDB (JSON).

## Prerequisites
- Render account
- Git repository with your code
- (Optional) PostgreSQL or MongoDB database

## recommended Setup: Using PostgreSQL

### Step 1: Create a PostgreSQL Database on Render
1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New** → **PostgreSQL**
3. Fill in the database name (e.g., `expense_tracker_db`)
4. Choose a region close to you
5. Select free tier if available
6. Click **Create Database**
7. Copy the **Internal Database URL** (you'll need it in Step 3)

### Step 2: Create a Web Service on Render
1. Click **New** → **Web Service**
2. Connect your GitHub repository
3. Fill in the service name (e.g., `expense-tracker`)
4. Environment: **Python 3**
5. Build Command: `pip install -r requirements.txt`
6. Start Command: `gunicorn app:app`
7. Click **Create Web Service**

### Step 3: Configure Environment Variables
In your Render service dashboard:

1. Go to **Environment**
2. Add the following variables:
   ```
   FLASK_ENV=production
   SECRET_KEY=<generate-a-random-secure-key>
   SESSION_COOKIE_SECURE=True
   DATABASE_URL=<paste-your-postgresql-internal-url>
   ```

3. To generate a secure SECRET_KEY, run locally:
   ```python
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
4. Copy the output and paste it as the SECRET_KEY value

### Step 4: Connect the Database Service
1. In your web service settings, scroll to **Database** (if available)
2. Or manually connect by adding the DATABASE_URL to environment variables

## Alternative: Using MongoDB

### Environment Variables for MongoDB
```
DATABASE_URL=mongodb+srv://username:password@cluster.mongodb.net/expense_tracker_db
FLASK_ENV=production
SECRET_KEY=<your-secure-key>
SESSION_COOKIE_SECURE=True
```

## Supported Database Backends

### 1. PostgreSQL (Recommended for Production)
- **Pros**: Reliable, scalable, free tier available
- **Configuration**: Set `DATABASE_URL` to PostgreSQL connection string
- **Format**: `postgresql://user:password@host:port/database`

### 2. MongoDB (if using MongoDB Atlas)
- **Pros**: NoSQL, easy setup with Atlas free tier
- **Configuration**: Set `DATABASE_URL` to MongoDB connection string
- **Format**: `mongodb+srv://user:password@cluster.mongodb.net/database`

### 3. SQLite (Local Development Only)
- **Warning**: Do NOT use in Render production (files are ephemeral)
- **Configuration**: Leave `DATABASE_URL` empty or unset
- **Note**: Data will NOT persist on Render

### 4. TinyDB (Development Only)
- **Configuration**: Set `DATA_BACKEND=json`
- **Warning**: Not suitable for production or multiple instances

## Deployment Checklist

- [ ] Forked/cloned repository to your Git service (GitHub, GitLab, etc.)
- [ ] Created PostgreSQL database on Render (or MongoDB Atlas)
- [ ] Created Web Service on Render
- [ ] Added `FLASK_ENV=production` environment variable
- [ ] Added secure `SECRET_KEY` environment variable
- [ ] Added `DATABASE_URL` (PostgreSQL or MongoDB)
- [ ] Added `SESSION_COOKIE_SECURE=True`
- [ ] Deployed the service
- [ ] Tested login and expense tracking features

## Troubleshooting

### Application won't start
- Check the **Logs** tab in Render dashboard
- Verify all required environment variables are set
- Ensure DATABASE_URL is correct and accessible

### Database connection errors
- Verify DATABASE_URL format
- For PostgreSQL: Check if Render's IP is allowed
- For MongoDB: Ensure Atlas network access is configured

### Session/Login issues
- Set `SESSION_COOKIE_SECURE=True` for production
- Verify `SECRET_KEY` is set and is a secure random value

### Port Issues
- Render automatically assigns a PORT environment variable
- The app is configured to use PORT automatically (default: 8080)

## First Time Setup After Deployment

1. Navigate to your deployed app URL
2. Click **Register** to create a new account
3. Start adding expenses
4. View analytics and statistics

## File Structure

```
expense_tracker/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Procfile              # Render configuration
├── runtime.txt           # Python version specification
├── ENV.example           # Example environment configuration
├── template/
│   ├── index.html       # Dashboard
│   └── login.html       # Login/Register page
├── view_user_expenses.py # Utility script for viewing expenses
└── README.md            # This file
```

## Features

- **User Authentication**: Secure login and registration
- **Expense Management**: Add, view, and delete expenses
- **Analytics**: View spending statistics by category and time period
- **Responsive Design**: Works on desktop and mobile devices
- **Multi-Database Support**: PostgreSQL, MongoDB, SQLite, or TinyDB

## Data Security

- Passwords are hashed using Werkzeug's secure hash
- Session cookies are HTTP-only and secure
- CSRF protection is built-in
- Database connections are encrypted (for PostgreSQL/MongoDB)

## Performance Considerations

- Use PostgreSQL for production (best performance)
- Monitor Render's resource usage
- Scale up if needed based on traffic

## Maintenance

- Regularly check Render dashboard logs
- Monitor database usage
- Update dependencies periodically by re-deploying

## Support

For Render-specific issues, visit: https://render.com/docs
For Flask issues, visit: https://flask.palletsprojects.com/

---

**Happy expense tracking!**
