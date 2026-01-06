"""
Input validation functions for security and data integrity
"""
import re
from logger_setup import log

def validate_email(email):
    """
    Validate email format
    Returns: (is_valid, error_message)
    """
    if not email or not email.strip():
        return False, "Email cannot be empty"
    
    # Email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email.strip()):
        return False, "Invalid email format. Example: user@example.com"
    
    return True, ""

def validate_phone(phone):
    """
    Validate phone number (only digits allowed)
    Returns: (is_valid, error_message)
    """
    if not phone or not phone.strip():
        return False, "Phone number cannot be empty"
    
    # Remove common separators
    cleaned = phone.replace("-", "").replace(" ", "").replace("(", "").replace(")", "").replace("+", "")
    
    # Check if only digits
    if not cleaned.isdigit():
        return False, "Phone number can only contain digits (0-9)"
    
    # Check length (10-15 digits is reasonable for most countries)
    if len(cleaned) < 10 or len(cleaned) > 15:
        return False, "Phone number must be 10-15 digits"
    
    return True, ""

def validate_name(name):
    """
    Validate name (only letters and spaces)
    Returns: (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "Name cannot be empty"
    
    # Allow letters, spaces, hyphens, apostrophes
    pattern = r"^[a-zA-Z\s\-']+$"
    
    if not re.match(pattern, name.strip()):
        return False, "Name can only contain letters, spaces, hyphens, and apostrophes"
    
    # Check minimum length
    if len(name.strip()) < 2:
        return False, "Name must be at least 2 characters"
    
    return True, ""

def validate_password(password):
    """
    Validate password strength
    Requirements:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number
    - At least 1 special character
    
    Returns: (is_valid, error_message)
    """
    if not password:
        return False, "Password cannot be empty"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character (!@#$%^&*...)"
    
    return True, ""

def sanitize_phone(phone):
    """
    Clean phone number to only digits
    """
    if not phone:
        return ""
    return re.sub(r'[^\d]', '', phone)

def sanitize_name(name):
    """
    Clean name to only allowed characters
    """
    if not name:
        return ""
    # Keep only letters, spaces, hyphens, apostrophes
    return re.sub(r"[^a-zA-Z\s\-']", '', name).strip()

def sanitize_email(email):
    """
    Clean email (lowercase, trim)
    """
    if not email:
        return ""
    return email.strip().lower()

# Password strength indicator
def get_password_strength(password):
    """
    Returns password strength: weak, medium, strong
    """
    if not password:
        return "weak"
    
    score = 0
    
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if re.search(r'[A-Z]', password):
        score += 1
    if re.search(r'[a-z]', password):
        score += 1
    if re.search(r'\d', password):
        score += 1
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
    
    if score <= 2:
        return "weak"
    elif score <= 4:
        return "medium"
    else:
        return "strong"
