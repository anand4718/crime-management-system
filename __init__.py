from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_caching import Cache

# 1. Initialize the app
app = Flask(__name__)

# 2. Add configuration
app.config['SECRET_KEY'] = 'a_very_secret_key_change_this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email Configuration (IMPORTANT: Set your credentials)
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'  # <-- ENTER YOUR GMAIL
app.config['MAIL_PASSWORD'] = 'your_google_app_password' # <-- ENTER YOUR APP PASSWORD

# Caching Configuration
app.config['CACHE_TYPE'] = 'simple'

# 3. Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
mail = Mail(app)
cache = Cache(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# 4. Import routes at the end to avoid circular imports
from app import routes