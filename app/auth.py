from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__, template_folder='templates')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        
        if not email or not password or not first_name or not last_name:
            flash('All fields are required', 'error')
            return redirect(url_for('auth.signup'))
        if password != confirm:
            flash('Passwords do not match', 'error')
            return redirect(url_for('auth.signup'))
        
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('An account with that email already exists', 'error')
            return redirect(url_for('auth.signup'))
        
        user = User(
            email=email, 
            first_name=first_name, 
            last_name=last_name,
            name=f"{first_name} {last_name}"  # Keep for backward compatibility
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Welcome to Flik.ai!', 'success')
        return redirect(url_for('main.index'))
    
    return render_template('auth_signup.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully', 'success')
            next_url = request.args.get('next') or url_for('main.index')
            return redirect(next_url)
        
        flash('Invalid email or password', 'error')
        return redirect(url_for('auth.login'))
    
    return render_template('auth_login.html')

@auth_bp.route('/profile')
@login_required
def profile():
    from app.models import Document, Todo
    
    # Get user statistics
    total_documents = Document.query.count()
    total_todos = Todo.query.count()
    
    return render_template('profile.html', 
                         total_documents=total_documents,
                         total_todos=total_todos)

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        
        if not first_name or not last_name or not email:
            flash('All fields are required', 'error')
            return redirect(url_for('auth.edit_profile'))
        
        # Check if email is already taken by another user
        existing = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing:
            flash('An account with that email already exists', 'error')
            return redirect(url_for('auth.edit_profile'))
        
        # Update user fields, handling cases where columns might not exist
        if hasattr(current_user, 'first_name'):
            current_user.first_name = first_name
        if hasattr(current_user, 'last_name'):
            current_user.last_name = last_name
        current_user.email = email
        current_user.name = f"{first_name} {last_name}"  # Update for backward compatibility
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('edit_profile.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out', 'success')
    return redirect(url_for('auth.login'))
