# 🚀 Flik.ai - AI Document Assistant

A modern web application that lets you upload documents, extract text with AI, and search through your files with ease.

## ✨ Features

### 🗂 File Management
- Upload documents (PDF, DOCX, TXT, PNG, JPG, JPEG)
- Secure local storage
- File preview and download
- Delete files with confirmation

### 📖 Document Processing
- **PDF Text Extraction** - Extract text from PDF documents
- **OCR for Images** - Extract text from images using Tesseract OCR
- **Word Document Processing** - Extract text from DOCX files
- **Plain Text Support** - Direct text file reading

### 🔍 Search & Browse
- Search through filenames and extracted text
- Sort by upload date
- File type indicators
- Text extraction status

### 🎨 Modern UI
- Clean, responsive design
- Card-based file layout
- Drag & drop upload
- Mobile-friendly interface

## 🛠 Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite
- **Text Extraction**: 
  - `pdfplumber` for PDFs
  - `pytesseract` for OCR
  - `python-docx` for Word documents
- **Frontend**: Jinja2 templates + Custom CSS
- **Storage**: Local file system

## 🚀 Quick Start

### Option 1: Automated Setup
```bash
python setup.py
```

### Option 2: Manual Setup

1. **Create virtual environment**
```bash
python -m venv venv
```

2. **Activate virtual environment**
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
python run.py
```

5. **Open your browser**
Navigate to: http://localhost:5000

## 📋 Prerequisites

### Required
- Python 3.7+
- pip

### Optional (for OCR functionality)
- **Tesseract OCR**:
  - Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
  - macOS: `brew install tesseract`
  - Ubuntu: `sudo apt install tesseract-ocr`

## 📁 Project Structure

```
flik-ai/
├─ run.py                    # Main entry point
├─ setup.py                  # Setup script
├─ requirements.txt          # Dependencies
├─ app/
│  ├─ __init__.py           # Flask app factory
│  ├─ models.py             # Database models
│  ├─ routes.py             # Application routes
│  ├─ utils.py              # Utility functions
│  └─ templates/
│     ├─ base.html          # Base template
│     ├─ index.html         # Dashboard
│     ├─ upload.html        # Upload page
│     └─ file_detail.html   # File details
│  └─ static/
│     └─ css/
│         └─ style.css      # Styling
└─ uploads/                 # File storage
```

## 🎯 Usage

1. **Upload Documents**: Click "Upload" and select your files
2. **View Dashboard**: See all uploaded files with metadata
3. **Search**: Use the search bar to find specific documents
4. **View Details**: Click "View Details" to see extracted text
5. **Download**: Click "Open File" to view/download the original file

## 🔧 Configuration

The application uses these default settings:
- **Upload Limit**: 50MB per file
- **Database**: SQLite (flik_ai.db)
- **Storage**: Local uploads/ folder
- **Port**: 5000

## 🚀 Deployment

For production deployment:

1. **Set environment variables**:
```bash
export FLASK_ENV=production
export SECRET_KEY=your-secret-key-here
```

2. **Use a production WSGI server**:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

## 🔮 Future Features

- [ ] User authentication
- [ ] AI-powered document summaries
- [ ] Chat with documents
- [ ] Document categorization
- [ ] Cloud storage integration
- [ ] API endpoints
- [ ] Multi-user workspaces

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🆘 Support

If you encounter any issues:
1. Check the prerequisites
2. Ensure all dependencies are installed
3. Check the console for error messages
4. Open an issue on GitHub

---

**Made with ❤️ for document management**

## Environment Configuration

Create a .env file (or use environment variables) with keys depending on which integrations you enable:

```env
# Flask
FLASK_ENV=development
SECRET_KEY=change-this-in-production

# Storage (choose one)
UPLOAD_FOLDER=uploads
GCS_BUCKET_NAME=
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# Google Document AI (optional)
GOOGLE_PROJECT_ID=
GOOGLE_LOCATION=us
GOOGLE_PROCESSOR_ID=your-documentai-processor-id

# Google Calendar (optional)
GOOGLE_CALENDAR_CLIENT_ID=
GOOGLE_CALENDAR_CLIENT_SECRET=
GOOGLE_CALENDAR_REDIRECT_URI=

# Firebase Admin (optional for notifications and auth)
FIREBASE_CREDENTIALS=path/to/firebase-service-account.json
FIREBASE_PROJECT_ID=your-firebase-project-id

 

# Email (optional)
SENDGRID_API_KEY=
DEFAULT_FROM_EMAIL=
```

These services are optional. The app runs locally without them. Enable as you grow into AI classification, cloud OCR, calendar sync, and notifications.

### Gemini (Google Generative AI)

To enable Gemini-based document analysis (classification, todos, entities), set:

```env
GEMINI_API_KEY=AIzaSyB77ajkeupGgGhuUglwzynBzhE_SW8pQ2M
```

The app will automatically use Gemini when this key is present; otherwise it falls back to local keyword/regex processing.
