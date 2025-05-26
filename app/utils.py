from datetime import date, datetime
import zipfile
import re

ALLOWED_EXTENSIONS = {'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file(file):
    header = file.read(4)
    file.seek(0)
    if header == b'%PDF-':
        return True
    elif header == b'PK\x03\x04':
        z = zipfile.ZipFile(file)
        if 'word/document.xml' in z.namelist():
            return True
        else:
            return False
    else:
        return False
    
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def ensure_date(value):
    if value == None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return datetime.strptime(value, '%Y-%m-%d').date()
