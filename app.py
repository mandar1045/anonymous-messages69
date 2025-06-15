from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message as EmailMessage
from datetime import datetime
import os
from dotenv import load_dotenv
from flask_migrate import Migrate
from sqlalchemy import func

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///messages.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'your-app-password')

# For Vercel deployment
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    messages_received = db.relationship('Message', backref='recipient', lazy=True, foreign_keys='Message.recipient_id')
    messages_sent = db.relationship('Message', backref='sender', lazy=True, foreign_keys='Message.sender_id')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(50))
    is_anonymous = db.Column(db.Boolean, default=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reactions = db.relationship('Reaction', backref='message', lazy=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True)
    replies = db.relationship('Message', backref=db.backref('parent', remote_side=[id]), lazy=True)

class Reaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emoji = db.Column(db.String(10), nullable=False)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    total_users = User.query.count()
    total_messages = Message.query.count()
    total_reactions = Reaction.query.count()
    total_anonymous = Message.query.filter_by(is_anonymous=True).count()
    
    # Get most active category
    category_counts = db.session.query(
        Message.category, 
        func.count(Message.id)
    ).group_by(Message.category).all()
    
    if category_counts:
        most_active_category, most_active_category_count = max(category_counts, key=lambda x: x[1])
    else:
        most_active_category = None
        most_active_category_count = 0
    
    # Get all registered users ordered by username
    registered_users = User.query.order_by(User.username).all()
    
    return render_template('index.html',
                         total_users=total_users,
                         total_messages=total_messages,
                         total_reactions=total_reactions,
                         total_anonymous=total_anonymous,
                         most_active_category=most_active_category,
                         most_active_category_count=most_active_category_count,
                         registered_users=registered_users)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', 'false') == 'true'
        
        if not username or not password:
            flash('Please enter both username and password')
            return render_template('login.html')
            
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard')
            return redirect(next_page)
        
        flash('Invalid username or password')
        return render_template('login.html')
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    received_messages = Message.query.filter_by(recipient_id=current_user.id).order_by(Message.timestamp.desc()).all()
    sent_messages = Message.query.filter_by(sender_id=current_user.id).order_by(Message.timestamp.desc()).all()
    return render_template('dashboard.html', received_messages=received_messages, sent_messages=sent_messages)

@app.route('/send', methods=['POST'])
def send_message():
    recipient_username = request.form.get('recipient')
    content = request.form.get('message')
    category = request.form.get('category')
    is_anonymous = request.form.get('anonymous', 'false') == 'true'
    
    if not content:
        flash('Message content cannot be empty')
        return redirect(url_for('home'))
    
    recipient = User.query.filter_by(username=recipient_username).first()
    if not recipient:
        flash('Recipient not found')
        return redirect(url_for('home'))
    
    try:
        message = Message(
            content=content,
            category=category,
            is_anonymous=is_anonymous,
            sender_id=current_user.id if not is_anonymous and current_user.is_authenticated else None,
            recipient_id=recipient.id
        )
        
        db.session.add(message)
        db.session.commit()
        
        # Send email notification only if email is configured
        if recipient.email and app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
            try:
                email_msg = EmailMessage(
                    subject='New Anonymous Message',
                    recipients=[recipient.email],
                    body=f'You have received a new anonymous message!'
                )
                mail.send(email_msg)
            except Exception as e:
                app.logger.error(f'Error sending email: {str(e)}')
                # Don't fail the whole request if email fails
        
        flash('Message sent successfully!')
    except Exception as e:
        db.session.rollback()
        flash('Error sending message. Please try again.')
        app.logger.error(f'Error sending message: {str(e)}')
    
    return redirect(url_for('home'))

@app.route('/messages/<username>')
@login_required
def view_messages(username):
    user = User.query.filter_by(username=username).first_or_404()
    messages = Message.query.filter_by(recipient_id=user.id).order_by(Message.timestamp.desc()).all()
    return render_template('view_messages.html', user=user, messages=messages)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    
    messages = Message.query
    if query:
        messages = messages.filter(Message.content.ilike(f'%{query}%'))
    if category:
        messages = messages.filter_by(category=category)
    
    messages = messages.order_by(Message.timestamp.desc()).all()
    return render_template('search.html', messages=messages, query=query, category=category)

@app.route('/react/<int:message_id>', methods=['POST'])
@login_required
def react_to_message(message_id):
    emoji = request.form.get('emoji')
    message = Message.query.get_or_404(message_id)
    
    existing_reaction = Reaction.query.filter_by(
        message_id=message_id,
        user_id=current_user.id,
        emoji=emoji
    ).first()
    
    if existing_reaction:
        db.session.delete(existing_reaction)
    else:
        reaction = Reaction(emoji=emoji, message_id=message_id, user_id=current_user.id)
        db.session.add(reaction)
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/reply/<int:message_id>', methods=['POST'])
@login_required
def reply_to_message(message_id):
    parent_message = Message.query.get_or_404(message_id)
    content = request.form.get('content')
    is_anonymous = request.form.get('anonymous', 'false') == 'true'
    
    if not content:
        flash('Reply content cannot be empty')
        return redirect(url_for('dashboard'))
    
    try:
        # Determine the recipient - if the original message was anonymous, reply to the original recipient
        recipient_id = parent_message.sender_id if parent_message.sender_id else parent_message.recipient_id
        
        reply = Message(
            content=content,
            category=parent_message.category,
            is_anonymous=is_anonymous,
            sender_id=current_user.id if not is_anonymous else None,
            recipient_id=recipient_id,
            parent_id=message_id
        )
        
        db.session.add(reply)
        db.session.commit()
        
        # Send email notification
        recipient = User.query.get(recipient_id)
        if recipient and recipient.email and app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
            try:
                email_msg = EmailMessage(
                    subject='New Reply to Your Message',
                    recipients=[recipient.email],
                    body=f'You have received a reply to your message!'
                )
                mail.send(email_msg)
            except Exception as e:
                app.logger.error(f'Error sending email: {str(e)}')
        
        flash('Reply sent successfully!')
    except Exception as e:
        db.session.rollback()
        flash('Error sending reply. Please try again.')
        app.logger.error(f'Error sending reply: {str(e)}')
    
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True) 