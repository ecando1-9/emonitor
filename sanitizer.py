"""
Input sanitization module to prevent injection attacks and data corruption.
Provides sanitization functions for text input, email, phone numbers, etc.
"""
import re
import html
import json
from logger_setup import log

# HTML/SQL injection patterns
DANGEROUS_PATTERNS = [
    r'<script[^>]*>.*?</script>',  # Script tags
    r'javascript:',  # JavaScript protocol
    r'on\w+\s*=',  # Event handlers (onclick, etc.)
    r"['\";].*?(union|select|insert|update|delete|drop|exec|execute)",  # SQL injection
    r'--\s*$',  # SQL comments
    r'\/\*.*?\*\/',  # SQL multi-line comments
]

def sanitize_text(text, max_length=500, allow_newlines=False):
    """
    Sanitize general text input.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        allow_newlines: Whether to allow newline characters
    
    Returns:
        Sanitized text string
    """
    if not isinstance(text, str):
        text = str(text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            log.warning(f"Dangerous pattern detected in text input: {pattern[:50]}...")
            return ""
    
    # Remove or replace certain control characters
    if not allow_newlines:
        text = ' '.join(text.split())  # Replace multiple spaces/newlines with single space
    else:
        # If newlines allowed, still remove other control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # HTML encode potentially dangerous characters
    text = html.escape(text, quote=True)
    
    # Enforce length limit
    if len(text) > max_length:
        log.warning(f"Text input exceeded max length {max_length}, truncating")
        text = text[:max_length]
    
    return text

def sanitize_email(email):
    """
    Sanitize and validate email address.
    
    Args:
        email: Email address to sanitize
    
    Returns:
        Sanitized email or empty string if invalid
    """
    if not isinstance(email, str):
        return ""
    
    email = email.strip().lower()
    
    # Basic email validation pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        log.warning(f"Invalid email format: {email[:20]}...")
        return ""
    
    # Remove any null bytes or control characters
    email = email.replace('\x00', '')
    
    # Enforce reasonable length limit
    if len(email) > 254:  # RFC 5321
        return ""
    
    return email

def sanitize_phone(phone):
    """
    Sanitize phone number - remove non-numeric characters except + and -.
    
    Args:
        phone: Phone number to sanitize
    
    Returns:
        Sanitized phone number
    """
    if not isinstance(phone, str):
        phone = str(phone)
    
    phone = phone.strip()
    
    # Keep only digits, +, -, (), and spaces
    phone = re.sub(r'[^\d+\-\(\)\s]', '', phone)
    
    # Remove null bytes
    phone = phone.replace('\x00', '')
    
    # Enforce reasonable length limit (typically max 15 for international)
    if len(phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')) > 15:
        phone = phone[:30]  # Truncate to prevent abuse
    
    if not phone:
        log.warning("Phone number sanitization resulted in empty string")
        return ""
    
    return phone

def sanitize_name(name, max_length=100):
    """
    Sanitize person's name.
    
    Args:
        name: Name to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized name
    """
    if not isinstance(name, str):
        name = str(name)
    
    name = name.strip()
    
    # Remove leading/trailing whitespace and collapse multiple spaces
    name = ' '.join(name.split())
    
    # Remove null bytes
    name = name.replace('\x00', '')
    
    # Allow letters, spaces, hyphens, apostrophes
    name = re.sub(r"[^a-zA-Z\s\-']", '', name)
    
    # HTML encode if needed
    name = html.escape(name, quote=True)
    
    # Enforce length limit
    if len(name) > max_length:
        name = name[:max_length].rsplit(' ', 1)[0]  # Trim at word boundary
    
    if not name:
        log.warning("Name sanitization resulted in empty string")
        return "Unknown"
    
    return name

def sanitize_relationship(relationship, max_length=50):
    """
    Sanitize relationship description (e.g., 'Mother', 'Best Friend', 'Doctor').
    
    Args:
        relationship: Relationship to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized relationship
    """
    if not isinstance(relationship, str):
        relationship = str(relationship)
    
    relationship = relationship.strip()
    
    # Remove leading/trailing whitespace and collapse multiple spaces
    relationship = ' '.join(relationship.split())
    
    # Remove null bytes
    relationship = relationship.replace('\x00', '')
    
    # Allow letters, spaces, hyphens
    relationship = re.sub(r"[^a-zA-Z\s\-]", '', relationship)
    
    # HTML encode
    relationship = html.escape(relationship, quote=True)
    
    # Enforce length limit
    if len(relationship) > max_length:
        relationship = relationship[:max_length]
    
    if not relationship:
        return "Other"
    
    return relationship

def sanitize_filename(filename, max_length=255):
    """
    Sanitize filename to prevent path traversal and invalid characters.
    
    Args:
        filename: Filename to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized filename
    """
    if not isinstance(filename, str):
        filename = str(filename)
    
    filename = filename.strip()
    
    # Remove null bytes
    filename = filename.replace('\x00', '')
    
    # Remove path separators and parent directory references
    filename = filename.replace('/', '').replace('\\', '')
    filename = filename.replace('..', '').replace('.', '', 1) if filename.startswith('.') else filename
    
    # Allow only safe characters: letters, numbers, hyphens, underscores, dots
    filename = re.sub(r'[^a-zA-Z0-9._\-]', '_', filename)
    
    # Remove leading dots (hidden files on Unix)
    while filename.startswith('.'):
        filename = filename[1:]
    
    # Enforce length limit
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name = max_length - len(ext) - 1
        filename = name[:max_name] + ('.' + ext if ext else '')
    
    if not filename:
        filename = "file"
    
    return filename

def sanitize_dict(data, schema=None):
    """
    Recursively sanitize dictionary values.
    
    Args:
        data: Dictionary to sanitize
        schema: Optional dict specifying sanitization rules for each key
                Format: {'key': 'type', ...} where type can be 'email', 'phone', 'text', 'name', etc.
    
    Returns:
        Sanitized dictionary
    """
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    
    for key, value in data.items():
        # Sanitize the key itself
        if not isinstance(key, str):
            continue
        
        key = sanitize_text(key, max_length=100, allow_newlines=False)
        if not key:
            continue
        
        # Sanitize value based on schema or type
        if schema and key in schema:
            sanitization_type = schema[key]
            
            if sanitization_type == 'email':
                value = sanitize_email(value)
            elif sanitization_type == 'phone':
                value = sanitize_phone(value)
            elif sanitization_type == 'name':
                value = sanitize_name(value)
            elif sanitization_type == 'relationship':
                value = sanitize_relationship(value)
            elif sanitization_type == 'text':
                value = sanitize_text(value, max_length=500)
            else:
                value = sanitize_text(str(value), max_length=500)
        else:
            # Default sanitization for unknown keys
            if isinstance(value, str):
                value = sanitize_text(value, max_length=500)
            elif isinstance(value, dict):
                value = sanitize_dict(value, schema)
            elif isinstance(value, list):
                value = [sanitize_dict(item, schema) if isinstance(item, dict) 
                        else sanitize_text(str(item), max_length=500) if isinstance(item, str) 
                        else item for item in value]
        
        sanitized[key] = value
    
    return sanitized

def sanitize_emergency_contact(contact_dict):
    """
    Sanitize an emergency contact object.
    
    Args:
        contact_dict: Dictionary with keys: name, phone, email, relationship
    
    Returns:
        Sanitized emergency contact dictionary
    """
    if not isinstance(contact_dict, dict):
        return {}
    
    schema = {
        'name': 'name',
        'phone': 'phone',
        'email': 'email',
        'relationship': 'relationship'
    }
    
    return sanitize_dict(contact_dict, schema)

def validate_json_jsonb(data):
    """
    Validate that data can be safely stored as JSONB.
    
    Args:
        data: Data to validate
    
    Returns:
        True if valid, False otherwise
    """
    try:
        # Try to serialize and deserialize
        json_str = json.dumps(data)
        json.loads(json_str)
        
        # Ensure it's not too large (JSONB limit is typically quite large, but let's be safe)
        if len(json_str) > 1000000:  # 1MB limit
            log.warning("JSONB data exceeds safe size limit")
            return False
        
        return True
    except (TypeError, ValueError) as e:
        log.warning(f"Data is not valid JSONB-compatible format: {e}")
        return False

# Export all sanitization functions
__all__ = [
    'sanitize_text',
    'sanitize_email',
    'sanitize_phone',
    'sanitize_name',
    'sanitize_relationship',
    'sanitize_filename',
    'sanitize_dict',
    'sanitize_emergency_contact',
    'validate_json_jsonb'
]
