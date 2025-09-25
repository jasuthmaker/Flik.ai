import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.utils import format_file_size
from dotenv import load_dotenv, find_dotenv
from flask_login import LoginManager

# Load .env as early as possible and from the project root if present
_DOTENV_PATH = find_dotenv()
if _DOTENV_PATH:
    load_dotenv(_DOTENV_PATH, override=True)
else:
    load_dotenv(override=True)

# Import after dotenv is loaded so AI flags see the key
try:
    from app.ai_processor import _HAS_GEMINI
except Exception:
    _HAS_GEMINI = False

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'


def create_app():
    app = Flask(__name__, instance_relative_config=False)
    upload_folder = os.getenv("UPLOAD_FOLDER") or os.path.join(app.root_path, "..", "uploads")
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-key-flik-ai"),
        UPLOAD_FOLDER=upload_folder,
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,  # 50MB upload limit
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.root_path, '..', 'flik_ai.db')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    # Print AI status
    try:
        dotenv_loaded = bool(_DOTENV_PATH)
        print(
            f"[Flik.ai] .env loaded: {dotenv_loaded} ({_DOTENV_PATH or 'default search'}) | "
            f"GEMINI_API_KEY set: {bool(os.getenv('GEMINI_API_KEY'))} | Gemini active: {_HAS_GEMINI}"
        )
    except Exception:
        pass

    app.jinja_env.filters['format_file_size'] = format_file_size

    with app.app_context():
        db.create_all()

    from .routes import bp
    app.register_blueprint(bp)

    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    return app

from app.models import User

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None
