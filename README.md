# Message Board Application

A Flask-based message board application that allows users to send and receive messages, with features like anonymous messaging, reactions, and email notifications.

## Features

- User registration and authentication
- Send and receive messages
- Anonymous messaging
- Message reactions
- Email notifications
- Message categories
- Search functionality

## Deployment

This application is deployed on Vercel.

### Local Development

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables in `.env`:
```
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///messages.db
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

4. Run the application:
```bash
python app.py
```

### Vercel Deployment

1. Install Vercel CLI:
```bash
npm install -g vercel
```

2. Login to Vercel:
```bash
vercel login
```

3. Deploy:
```bash
vercel
```

4. Set up environment variables in Vercel dashboard:
- SECRET_KEY
- DATABASE_URL
- MAIL_SERVER
- MAIL_PORT
- MAIL_USE_TLS
- MAIL_USERNAME
- MAIL_PASSWORD

## Technologies Used

- Flask
- SQLAlchemy
- Flask-Login
- Flask-Mail
- PostgreSQL (production)
- SQLite (development)
- Bootstrap
- Font Awesome 