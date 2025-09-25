import re
import nltk
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import logging
import os

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger')

# Optional Gemini
_HAS_GEMINI = False
try:
    import google.generativeai as genai
    if os.getenv('GEMINI_API_KEY'):
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        _HAS_GEMINI = True
except Exception:
    _HAS_GEMINI = False

class GeminiAnalyzer:
    """Use Gemini to classify document, extract todos, and entities."""
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.model_name = model_name
        if _HAS_GEMINI:
            self.model = genai.GenerativeModel(model_name)
        else:
            self.model = None

    def analyze(self, text: str, filename: str = "") -> Optional[Dict]:
        if not _HAS_GEMINI or not self.model or not text:
            return None
        system_prompt = (
            "You are a helpful assistant that reads a document's text and returns structured JSON. "
            "Classify into one of: Medical, Dental, Pharmacy, Insurance, Finance, ID, Legal, Other. "
            "Extract appointments (date/time if present), reminders/deadlines, and entities like doctor/hospital/medicine/insurance numbers. "
            "Return ONLY valid JSON with keys: category (string), todos (array of {type:'appointment'|'todo', title, description, due_date_iso|null, category}), entities (object)."
        )
        user_text = f"Filename: {filename}\n\nContent:\n{text[:8000]}"  # truncate to keep prompt small
        try:
            resp = self.model.generate_content([
                {"role": "user", "parts": [system_prompt]},
                {"role": "user", "parts": [user_text]}
            ])
            raw = resp.text or "{}"
            # Attempt to locate JSON in response
            import json
            json_text = raw.strip()
            # Loose guard: extract between first { and last }
            if not json_text.startswith('{'):
                l = json_text.find('{')
                r = json_text.rfind('}')
                if l != -1 and r != -1 and r > l:
                    json_text = json_text[l:r+1]
            data = json.loads(json_text)
            # Normalize keys
            category = data.get('category') or 'Other'
            todos = []
            for item in data.get('todos', []):
                todos.append({
                    'type': item.get('type') or 'todo',
                    'title': item.get('title') or 'Task',
                    'description': item.get('description') or '',
                    'due_date': self._parse_iso(item.get('due_date_iso')),
                    'category': category
                })
            entities = data.get('entities', {})
            return {'category': category, 'todos': todos, 'entities': entities}
        except Exception as e:
            logging.exception("Gemini analysis failed: %s", e)
            return None

    def _parse_iso(self, iso_str: Optional[str]) -> Optional[datetime]:
        if not iso_str:
            return None
        try:
            from dateutil import parser
            return parser.parse(iso_str)
        except Exception:
            return None

class DocumentCategorizer:
    """AI-powered document categorization using keyword matching and ML"""
    
    def __init__(self):
        self.categories = {
            'Medical': {
                'keywords': [
                    'doctor', 'physician', 'medical', 'hospital', 'clinic', 'patient', 'diagnosis',
                    'treatment', 'surgery', 'medication', 'health', 'illness',
                    'symptoms', 'medical record', 'lab results', 'blood test', 'x-ray', 'mri',
                    'ct scan', 'ultrasound', 'biopsy', 'therapy', 'rehabilitation'
                ],
                'triggers': ['medical', 'doctor', 'hospital', 'clinic', 'patient', 'lab', 'results'],
                'weight': 1.0
            },
            'Dental': {
                'keywords': [
                    'dentist', 'dental', 'tooth', 'teeth', 'oral', 'cleaning', 'cavity',
                    'filling', 'root canal', 'extraction', 'braces', 'orthodontist',
                    'gum', 'periodontal', 'dental checkup', 'dental appointment'
                ],
                'triggers': ['dental', 'dentist', 'tooth', 'teeth', 'orthodont', 'periodontal', 'gum'],
                'weight': 1.0
            },
            'Pharmacy': {
                'keywords': [
                    'pharmacy', 'pharmacist', 'prescription', 'medication', 'drug', 'pill',
                    'refill', 'dosage', 'pharmaceutical', 'rx', 'medicine', 'tablet',
                    'capsule', 'syrup', 'injection', 'pharmacy receipt'
                ],
                'triggers': ['pharmacy', 'rx', 'prescription'],
                'weight': 1.0
            },
            'Insurance': {
                'keywords': [
                    'insurance', 'policy', 'coverage', 'premium', 'deductible', 'claim',
                    'benefits', 'copay', 'copayment', 'health insurance', 'medical insurance',
                    'dental insurance', 'vision insurance', 'life insurance', 'auto insurance'
                ],
                'triggers': ['insurance', 'policy', 'claim'],
                'weight': 1.0
            },
            'Finance': {
                'keywords': [
                    'bank', 'account', 'statement', 'transaction', 'deposit', 'withdrawal',
                    'credit card', 'debit', 'loan', 'mortgage', 'investment', 'portfolio',
                    'tax', 'irs', 'w-2', '1099', 'financial', 'budget', 'expense', 'invoice', 'bill'
                ],
                'triggers': ['invoice', 'bill', 'statement', 'payment'],
                'weight': 1.0
            },
            'ID': {
                'keywords': [
                    'id', 'identification', 'passport', 'driver license', 'social security',
                    'ssn', 'birth certificate', 'visa', 'green card', 'citizenship',
                    'identity', 'personal information'
                ],
                'triggers': ['passport', 'driver', 'ssn', 'identity'],
                'weight': 1.0
            },
            'Legal': {
                'keywords': [
                    'legal', 'lawyer', 'attorney', 'court', 'lawsuit', 'contract',
                    'agreement', 'lease', 'will', 'trust', 'power of attorney',
                    'legal document', 'notary', 'legal advice'
                ],
                'triggers': ['legal', 'attorney', 'contract', 'court'],
                'weight': 1.0
            }
        }
    
    def _count_occurrences(self, haystack: str, terms: list[str]) -> int:
        count = 0
        for t in terms:
            if not t:
                continue
            count += haystack.count(t.lower())
        return count
    
    def categorize_document(self, text: str, filename: str = "") -> str:
        if not text and not filename:
            return 'Other'
        full_text = f"{filename} {text}".lower()

        # Base scores
        category_scores: dict[str, float] = {}
        trigger_hits: dict[str, int] = {}
        for category, config in self.categories.items():
            kw_score = self._count_occurrences(full_text, config.get('keywords', [])) * config.get('weight', 1.0)
            trig_count = self._count_occurrences(full_text, config.get('triggers', []))
            # Heavily weight triggers to reduce cross-category bleed
            score = kw_score + trig_count * 3.0
            category_scores[category] = score
            trigger_hits[category] = trig_count

        # If nothing matched, return Other
        best_category = max(category_scores, key=category_scores.get)
        if category_scores[best_category] <= 0:
            return 'Other'

        # Tie-breaks & Dental vs Medical disambiguation
        medical_score = category_scores.get('Medical', 0.0)
        dental_score = category_scores.get('Dental', 0.0)
        if medical_score > 0 and dental_score > 0:
            med_trigs = trigger_hits.get('Medical', 0)
            den_trigs = trigger_hits.get('Dental', 0)
            if den_trigs > med_trigs:
                return 'Dental'
            if med_trigs > den_trigs:
                return 'Medical'
            # Fallback: prefer Medical unless explicit dental words exist
            if any(w in full_text for w in self.categories['Dental']['triggers']):
                return 'Dental'
            return 'Medical'

        return best_category

class AppointmentExtractor:
    """Extract appointments and todos from document text"""
    
    def __init__(self):
        # Date patterns
        self.date_patterns = [
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4}\b',
            r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday),?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\b'
        ]
        
        # Time patterns
        self.time_patterns = [
            r'\b\d{1,2}:\d{2}\s*(?:am|pm)\b',
            r'\b\d{1,2}\s*(?:am|pm)\b',
            r'\b(?:morning|afternoon|evening|noon|midnight)\b'
        ]
        
        # Appointment/todo keywords
        self.appointment_keywords = [
            'appointment', 'meeting', 'visit', 'consultation', 'checkup', 'examination',
            'scheduled', 'booked', 'reserved', 'confirmed', 'reminder'
        ]
        
        self.todo_keywords = [
            'refill', 'renew', 'expires', 'due', 'deadline', 'reminder', 'follow up',
            'call', 'contact', 'schedule', 'book', 'make appointment', 'pay', 'submit'
        ]
    
    def extract_appointments_and_todos(self, text: str, category: str) -> List[Dict]:
        """Extract appointments and todos from document text"""
        if not text:
            return []
        
        text_lower = text.lower()
        results = []
        
        # Find dates
        dates = []
        for pattern in self.date_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                dates.append({
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end()
                })
        
        # Find times
        times = []
        for pattern in self.time_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                times.append({
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end()
                })
        
        # Look for appointment contexts
        for keyword in self.appointment_keywords:
            if keyword in text_lower:
                # Find sentences containing the keyword
                sentences = nltk.sent_tokenize(text)
                for sentence in sentences:
                    if keyword in sentence.lower():
                        # Try to extract date and time from the sentence
                        date_time = self._extract_date_time_from_sentence(sentence, dates, times)
                        
                        results.append({
                            'type': 'appointment',
                            'title': f"{category.title()} Appointment",
                            'description': sentence.strip(),
                            'due_date': date_time,
                            'category': category
                        })
                        break
        
        # Look for todo contexts
        for keyword in self.todo_keywords:
            if keyword in text_lower:
                sentences = nltk.sent_tokenize(text)
                for sentence in sentences:
                    if keyword in sentence.lower():
                        date_time = self._extract_date_time_from_sentence(sentence, dates, times)
                        
                        results.append({
                            'type': 'todo',
                            'title': f"{category.title()} Task",
                            'description': sentence.strip(),
                            'due_date': date_time,
                            'category': category
                        })
                        break
        
        return results
    
    def _extract_date_time_from_sentence(self, sentence: str, dates: List[Dict], times: List[Dict]) -> Optional[datetime]:
        """Extract date and time from a sentence"""
        sentence_lower = sentence.lower()
        
        # Find the closest date and time to the sentence
        closest_date = None
        closest_time = None
        
        for date_info in dates:
            if date_info['text'] in sentence_lower:
                closest_date = date_info['text']
                break
        
        for time_info in times:
            if time_info['text'] in sentence_lower:
                closest_time = time_info['text']
                break
        
        # Try to parse the date
        if closest_date:
            try:
                # Simple date parsing - you might want to use dateutil for more robust parsing
                parsed_date = self._parse_date(closest_date)
                if parsed_date:
                    return parsed_date
            except:
                pass
        
        return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse a date string to datetime object"""
        try:
            # Handle common date formats
            date_str = date_str.strip()
            
            # Month day, year format
            if ',' in date_str:
                return datetime.strptime(date_str, '%B %d, %Y')
            
            # MM/DD/YYYY format
            if '/' in date_str:
                return datetime.strptime(date_str, '%m/%d/%Y')
            
            # DD-MM-YYYY format
            if '-' in date_str and len(date_str.split('-')[0]) <= 2:
                return datetime.strptime(date_str, '%d-%m-%Y')
            
        except ValueError:
            pass
        
        return None

class AIProcessor:
    """Main AI processor that combines categorization and appointment extraction"""
    
    def __init__(self):
        self.categorizer = DocumentCategorizer()
        self.extractor = AppointmentExtractor()
        self.gemini = GeminiAnalyzer() if _HAS_GEMINI else None
    
    def process_document(self, text: str, filename: str = "") -> Tuple[str, List[Dict]]:
        """Process a document and return category and extracted todos/appointments"""
        if self.gemini:
            result = self.gemini.analyze(text, filename)
            if result:
                category = result.get('category') or 'Other'
                todos = result.get('todos') or []
                return category, todos
        # Fallback to local logic
        category = self.categorizer.categorize_document(text, filename)
        appointments_todos = self.extractor.extract_appointments_and_todos(text, category)
        return category, appointments_todos
