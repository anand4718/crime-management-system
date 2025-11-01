from flask import render_template, url_for, flash, redirect, request, jsonify
from app import app, db, mail, cache
from app.forms import RegistrationForm, LoginForm, ComplaintForm, PublicInfoForm
from app.models import User, Complaint, PublicInfo, Alert
from flask_login import login_user, current_user, logout_user, login_required
import json, os, secrets
from PIL import Image
from app.scraper import fetch_crime_news
from flask_mail import Message
from collections import Counter

# --- HELPER FUNCTION TO SAVE UPLOADED PICTURES ---
def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    # Resize image to save space and standardize size
    output_size = (250, 250)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

# --- AI Model for Complaint Categorization ---
keywords = { 'Theft': ['stole', 'robbed', 'theft'], 'Vandalism': ['vandalized', 'damaged'], 'Assault': ['assaulted', 'hit'], 'Cybercrime': ['hacked', 'scam'] }
sentiment_keywords = { 'Urgent': ['urgent', 'immediately', 'help'], 'Neutral': ['reporting', 'incident'] }
def classify_text(text, classification_dict):
    text = text.lower()
    for category, words in classification_dict.items():
        if any(word in text for word in words): return category
    return 'Uncategorized' if classification_dict == keywords else 'Neutral'

# --- Main Application Routes ---
@app.route("/")
@app.route("/home")
@cache.cached(timeout=300) # Caching for 5 minutes
def home():
    latest_news = fetch_crime_news()
    return render_template('index.html', title='Home', news_articles=latest_news)

# --- Public Info Routes ---
@app.route("/missing_persons")
def missing_persons():
    persons = PublicInfo.query.filter_by(category='Missing').order_by(PublicInfo.id.desc()).all()
    return render_template('missing_persons.html', title='Missing Persons', persons=persons)

@app.route("/most_wanted")
def most_wanted():
    criminals = PublicInfo.query.filter_by(category='Wanted').order_by(PublicInfo.id.desc()).all()
    return render_template('most_wanted.html', title='Most Wanted', criminals=criminals)

@app.route("/unidentified_bodies")
def unidentified_bodies():
    bodies = PublicInfo.query.filter_by(category='Unidentified').order_by(PublicInfo.id.desc()).all()
    return render_template('unidentified_bodies.html', title='Unidentified Bodies', bodies=bodies)

# --- Authentication and User Routes ---
@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=True)
            flash('You have been logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/dashboard")
@login_required
def user_dashboard():
    complaints = Complaint.query.filter_by(author=current_user).order_by(Complaint.id.desc()).all()
    return render_template('user_dashboard.html', title='Dashboard', complaints=complaints)

@app.route("/complaint/new", methods=['GET', 'POST'])
@login_required
def file_complaint():
    form = ComplaintForm()
    if form.validate_on_submit():
        description = form.description.data
        ai_category = classify_text(description, keywords)
        ai_sentiment = classify_text(description, sentiment_keywords)
        complaint = Complaint(title=form.title.data, description=description, location=form.location.data, author=current_user, category=ai_category, sentiment=ai_sentiment)
        db.session.add(complaint)
        db.session.commit()
        flash(f'Your complaint has been filed! AI has categorized it as "{ai_category}".', 'success')
        return redirect(url_for('user_dashboard'))
    return render_template('file_complaint.html', title='File Complaint', form=form)

# --- Admin Control Panel Routes ---
@app.route("/admin")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    form = PublicInfoForm()
    all_complaints = Complaint.query.order_by(Complaint.id.desc()).all()
    all_users = User.query.order_by(User.id.asc()).all()
    unread_alerts = Alert.query.filter_by(is_read=False).order_by(Alert.timestamp.desc()).all()
    return render_template('admin_dashboard.html', title='Admin Dashboard', complaints=all_complaints, users=all_users, form=form, alerts=unread_alerts)

@app.route("/admin/add_info", methods=['POST'])
@login_required
def add_public_info():
    if not current_user.is_admin: return redirect(url_for('home'))
    form = PublicInfoForm()
    if form.validate_on_submit():
        picture_file = 'default.jpg'
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
        new_info = PublicInfo(name=form.name.data, details=form.details.data, category=form.category.data, image_file=picture_file)
        db.session.add(new_info)
        db.session.commit()
        flash('New public record has been added successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/complaint/<int:complaint_id>/update_status", methods=['POST'])
@login_required
def update_complaint_status(complaint_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Permission denied.'}), 403
    
    complaint = Complaint.query.get_or_404(complaint_id)
    data = request.get_json()
    new_status = data.get('status') if data else request.form.get('status')

    if new_status and complaint.status != new_status:
        complaint.status = new_status
        db.session.commit()
        try:
            msg = Message('Your Complaint Status Has Been Updated', sender=app.config['MAIL_USERNAME'], recipients=[complaint.author.email])
            msg.html = render_template('email/status_update.html', user=complaint.author, complaint=complaint)
            mail.send(msg)
            message = f'Status for complaint #{complaint.id} updated to {new_status} and user notified.'
            return jsonify({'success': True, 'message': message})
        except Exception as e:
            message = f'Status updated, but failed to send email: {e}'
            return jsonify({'success': True, 'message': message})
            
    return jsonify({'success': False, 'message': 'No changes made.'})

@app.route("/admin/complaint/<int:complaint_id>/delete")
@login_required
def delete_complaint(complaint_id):
    if not current_user.is_admin: return redirect(url_for('home'))
    complaint = Complaint.query.get_or_404(complaint_id)
    db.session.delete(complaint)
    db.session.commit()
    flash(f'Complaint #{complaint.id} has been deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/user/<int:user_id>/delete")
@login_required
def delete_user(user_id):
    if not current_user.is_admin: return redirect(url_for('home'))
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete your own account.", 'danger')
        return redirect(url_for('admin_dashboard'))
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.username} has been deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/user/<int:user_id>/toggle_admin")
@login_required
def toggle_admin(user_id):
    if not current_user.is_admin: return redirect(url_for('home'))
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot change your own admin status.", 'danger')
        return redirect(url_for('admin_dashboard'))
    user.is_admin = not user.is_admin
    db.session.commit()
    status = "promoted to" if user.is_admin else "demoted from"
    flash(f'User {user.username} has been {status} admin.', 'success')
    return redirect(url_for('admin_dashboard'))

# --- Analytics Dashboard Route ---
@app.route("/admin/analytics")
@login_required
def analytics_dashboard():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    category_counts = dict(Counter(c.category for c in Complaint.query.all()))
    sentiment_counts = dict(Counter(c.sentiment for c in Complaint.query.all()))
    locations = [c.location for c in Complaint.query.filter(Complaint.location.isnot(None)).all()]
    return render_template('analytics.html', title='Analytics', category_data=category_counts, sentiment_data=sentiment_counts, location_data=locations)

# --- AI Chatbot Route ---
@app.route("/ask_ai", methods=['POST'])
def ask_ai():
    user_message = request.json['message'].lower()
    reply = "I'm sorry, I don't understand that question."
    if ("report" in user_message and "crime" in user_message) or \
       ("how" in user_message and ("file" in user_message or "report" in user_message or "complaint" in user_message)):
        reply = "You can report a crime by logging in and clicking the 'Report a Crime' link."
    elif "status" in user_message or ("check" in user_message and "complaint" in user_message):
        reply = "To check your complaint status, please log in and visit your Dashboard."
    elif "missing" in user_message and "person" in user_message:
        reply = "View missing persons reports by clicking the 'Missing Persons' link in the main navigation."
    elif "most wanted" in user_message:
        reply = "The 'Most Wanted' list is available by clicking the link in the navigation bar."
    elif "hello" in user_message or "hi" in user_message:
        reply = "Hello! How can I assist you with the Crime Management System today?"
    return json.dumps({'reply': reply})