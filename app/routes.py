import os
from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_login import current_user
from werkzeug.utils import secure_filename
from app.models import Document, Todo, db
from app.utils import extract_text_from_file, get_file_size, format_file_size, process_document_with_ai
from datetime import datetime, timedelta

bp = Blueprint("main", __name__, template_folder="templates", static_folder="static")

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "docx", "txt"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route("/")
def index():
    # Show landing page for anonymous users; dashboard for authenticated users
    if not current_user.is_authenticated:
        return render_template("landing.html")

    search_query = request.args.get('search', '')
    category_filter = request.args.get('category', '')

    # Base documents query (for list and counts)
    documents_q = Document.query

    if search_query:
        documents_q = documents_q.filter(
            (Document.filename.contains(search_query)) |
            (Document.original_filename.contains(search_query)) |
            (Document.extracted_text.contains(search_query))
        )

    if category_filter:
        documents_q = documents_q.filter(Document.category == category_filter)

    # Sorting controls
    sort = request.args.get('sort', 'date_desc')
    if sort == 'date_asc':
        documents_q = documents_q.order_by(Document.upload_date.asc())
    elif sort == 'name_asc':
        documents_q = documents_q.order_by(Document.original_filename.asc())
    elif sort == 'name_desc':
        documents_q = documents_q.order_by(Document.original_filename.desc())
    elif sort == 'size_asc':
        documents_q = documents_q.order_by(Document.file_size.asc())
    elif sort == 'size_desc':
        documents_q = documents_q.order_by(Document.file_size.desc())
    else:  # date_desc
        documents_q = documents_q.order_by(Document.upload_date.desc())

    documents = documents_q.all()

    # Sidebar categories and counts
    raw_counts = db.session.query(Document.category, db.func.count(Document.id)).group_by(Document.category).all()
    category_counts = {k or 'Other': v for k, v in raw_counts}
    categories = list(category_counts.keys())

    # Dashboard widgets
    recent_docs = Document.query.order_by(Document.upload_date.desc()).limit(5).all()
    upcoming_appointments = (
        Todo.query
        .filter(Todo.due_date.isnot(None))
        .order_by(Todo.due_date.asc())
        .limit(5)
        .all()
    )
    pending_todos = (
        Todo.query
        .filter((Todo.is_completed == False))
        .order_by(Todo.due_date.is_(None), Todo.due_date.asc())
        .limit(5)
        .all()
    )

    # Footer metrics
    total_documents = db.session.query(db.func.count(Document.id)).scalar() or 0
    total_pending_tasks = db.session.query(db.func.count(Todo.id)).filter(Todo.is_completed == False).scalar() or 0
    week_ago = datetime.utcnow() - timedelta(days=7)
    docs_this_week = db.session.query(db.func.count(Document.id)).filter(Document.upload_date >= week_ago).scalar() or 0
    ai_processed = db.session.query(db.func.count(Document.id)).filter(Document.extracted_text.isnot(None), Document.extracted_text != '').scalar() or 0

    return render_template(
        "index.html",
        documents=documents,
        search_query=search_query,
        categories=categories,
        selected_category=category_filter,
        category_counts=category_counts,
        recent_docs=recent_docs,
        upcoming_appointments=upcoming_appointments,
        pending_todos=pending_todos,
        total_documents=total_documents,
        total_pending_tasks=total_pending_tasks,
        docs_this_week=docs_this_week,
        ai_processed=ai_processed,
        sort=sort,
    )

@bp.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part", "error")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            flash("No selected file", "error")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            
            # avoid clobbering: if exists, append counter
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(save_path):
                filename = f"{base}_{counter}{ext}"
                save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                counter += 1
            
            file.save(save_path)
            
            # Get file info
            file_size = get_file_size(save_path)
            file_type = filename.rsplit(".", 1)[1].lower()
            
            # Extract text
            extracted_text = extract_text_from_file(save_path, file_type)
            
            # Process with AI for categorization and appointment extraction
            category, appointments_todos = process_document_with_ai(extracted_text, file.filename)
            
            # Save to database
            document = Document(
                filename=filename,
                original_filename=file.filename,
                file_path=save_path,
                file_size=file_size,
                file_type=file_type,
                extracted_text=extracted_text,
                category=category
            )
            
            db.session.add(document)
            db.session.flush()  # Get the document ID
            
            # Create todos/appointments from AI extraction
            for item in appointments_todos:
                todo = Todo(
                    title=item['title'],
                    description=item['description'],
                    due_date=item['due_date'],
                    category=item['category'],
                    document_id=document.id
                )
                db.session.add(todo)
            
            db.session.commit()
            
            flash(f"Uploaded: {filename}", "success")
            return redirect(url_for("main.index"))
        else:
            flash("File type not allowed", "error")
            return redirect(request.url)
    return render_template("upload.html")

@bp.route("/file/<int:file_id>")
def file_detail(file_id):
    document = Document.query.get_or_404(file_id)
    return render_template("file_detail.html", document=document)

@bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename, as_attachment=False)

@bp.route("/delete/<int:file_id>", methods=["POST"])
def delete_file(file_id):
    document = Document.query.get_or_404(file_id)
    
    # Delete physical file
    if os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    # Delete from database
    db.session.delete(document)
    db.session.commit()
    
    flash(f"Deleted: {document.filename}", "success")
    return redirect(url_for("main.index"))

@bp.route("/search")
def search():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('main.index'))
    
    documents = Document.query.filter(
        (Document.filename.contains(query)) |
        (Document.original_filename.contains(query)) |
        (Document.extracted_text.contains(query))
    ).order_by(Document.upload_date.desc()).all()
    
    return render_template("index.html", documents=documents, search_query=query)

@bp.route("/todos")
def todos():
    """Display todos and appointments page"""
    todos = Todo.query.order_by(Todo.due_date.asc()).all()
    return render_template("todos.html", todos=todos)

@bp.route("/update_category/<int:file_id>", methods=["POST"])
def update_category(file_id):
    """Update document category"""
    document = Document.query.get_or_404(file_id)
    new_category = request.form.get('category', 'Other')
    
    document.category = new_category
    db.session.commit()
    
    flash(f"Category updated to {new_category}", "success")
    return redirect(url_for("main.file_detail", file_id=file_id))

@bp.route("/toggle_todo/<int:todo_id>", methods=["POST"])
def toggle_todo(todo_id):
    """Toggle todo completion status"""
    todo = Todo.query.get_or_404(todo_id)
    todo.is_completed = not todo.is_completed
    db.session.commit()
    
    return jsonify({'success': True, 'is_completed': todo.is_completed})

@bp.route("/delete_todo/<int:todo_id>", methods=["POST"])
def delete_todo(todo_id):
    """Delete a todo"""
    todo = Todo.query.get_or_404(todo_id)
    db.session.delete(todo)
    db.session.commit()
    
    flash("Todo deleted successfully", "success")
    return redirect(url_for("main.todos"))

@bp.route("/add_task", methods=["POST"])
def add_task():
    """Add a new task via AJAX"""
    try:
        title = request.form.get('title', '').strip()
        due_date_str = request.form.get('due_date', '')
        
        if not title:
            return jsonify({'success': False, 'error': 'Task title is required'})
        
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid date format'})
        
        todo = Todo(title=title, due_date=due_date)
        db.session.add(todo)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Task added successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@bp.route("/calendar")
def calendar():
    """Calendar page with appointments and tasks"""
    # Get all appointments and tasks with due dates
    appointments_query = Todo.query.filter(Todo.due_date.isnot(None)).order_by(Todo.due_date.asc()).all()
    
    # Convert to dictionaries for JSON serialization
    appointments = []
    for appointment in appointments_query:
        appointments.append({
            'id': appointment.id,
            'title': appointment.title,
            'description': appointment.description,
            'due_date': appointment.due_date.isoformat() if appointment.due_date else None,
            'is_completed': appointment.is_completed,
            'category': appointment.category
        })
    
    # Group by month for calendar display
    current_date = datetime.now()
    calendar_data = {}
    
    for appointment in appointments:
        if appointment['due_date']:
            due_date = datetime.fromisoformat(appointment['due_date'])
            month_key = due_date.strftime("%Y-%m")
            if month_key not in calendar_data:
                calendar_data[month_key] = []
            calendar_data[month_key].append(appointment)
    
    # Get current month data
    current_month = current_date.strftime("%Y-%m")
    current_month_appointments = calendar_data.get(current_month, [])
    
    return render_template("calendar.html", 
                         appointments=appointments,
                         current_month_appointments=current_month_appointments,
                         current_date=current_date)

@bp.route("/insights")
def insights():
    """Analytics and insights page"""
    # Document analytics
    total_docs = Document.query.count()
    docs_by_type_query = db.session.query(Document.file_type, db.func.count(Document.id)).group_by(Document.file_type).all()
    docs_by_category_query = db.session.query(Document.category, db.func.count(Document.id)).group_by(Document.category).all()
    
    # Convert Row objects to lists of tuples
    docs_by_type = [(row[0], row[1]) for row in docs_by_type_query]
    docs_by_category = [(row[0], row[1]) for row in docs_by_category_query]
    
    # Recent activity (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_uploads = Document.query.filter(Document.upload_date >= thirty_days_ago).count()
    
    # Task analytics
    total_tasks = Todo.query.count()
    completed_tasks = Todo.query.filter(Todo.is_completed == True).count()
    pending_tasks = total_tasks - completed_tasks
    
    # Monthly upload trends
    monthly_uploads = []
    for i in range(6):  # Last 6 months
        month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        count = Document.query.filter(
            Document.upload_date >= month_start,
            Document.upload_date < month_end
        ).count()
        monthly_uploads.append({
            'month': month_start.strftime('%b %Y'),
            'count': count
        })
    monthly_uploads.reverse()
    
    return render_template("insights.html",
                         total_docs=total_docs,
                         docs_by_type=docs_by_type,
                         docs_by_category=docs_by_category,
                         recent_uploads=recent_uploads,
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         pending_tasks=pending_tasks,
                         monthly_uploads=monthly_uploads)