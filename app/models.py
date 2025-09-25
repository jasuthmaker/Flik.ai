from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    extracted_text = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False, default='Other')
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Document {self.filename}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'category': self.category,
            'upload_date': self.upload_date.isoformat(),
            'has_text': bool(self.extracted_text)
        }

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    category = db.Column(db.String(50), nullable=False, default='Other')
    is_completed = db.Column(db.Boolean, default=False)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    document = db.relationship('Document', backref=db.backref('todos', lazy=True))
    
    def __repr__(self):
        return f'<Todo {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'category': self.category,
            'is_completed': self.is_completed,
            'document_id': self.document_id,
            'created_date': self.created_date.isoformat()
        }

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(255), nullable=True)  # Keep for backward compatibility
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        # Handle backward compatibility for existing users
        if hasattr(self, 'first_name') and hasattr(self, 'last_name') and self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif hasattr(self, 'name') and self.name:
            return self.name
        else:
            return "User"
    
    def get_initials(self):
        # Handle backward compatibility for existing users
        if hasattr(self, 'first_name') and hasattr(self, 'last_name') and self.first_name and self.last_name:
            return f"{self.first_name[0] if self.first_name else ''}{self.last_name[0] if self.last_name else ''}".upper()
        elif hasattr(self, 'name') and self.name:
            # Extract initials from the name field
            name_parts = self.name.strip().split(' ')
            if len(name_parts) >= 2:
                return f"{name_parts[0][0] if name_parts[0] else ''}{name_parts[1][0] if name_parts[1] else ''}".upper()
            elif len(name_parts) == 1:
                return name_parts[0][0].upper() if name_parts[0] else 'U'
            else:
                return 'U'
        else:
            return 'U'

    def __repr__(self):
        return f'<User {self.email}>'
