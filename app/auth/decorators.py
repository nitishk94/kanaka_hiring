from flask_login import current_user
from functools import wraps
from flask import redirect, url_for, flash

def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Login required", "warning")
                return redirect(url_for('<login page>'))

            if current_user.role not in roles:
                flash("Access denied: insufficient permissions", "danger")
                return redirect(url_for('<home page>'))

            return view_func(*args, **kwargs)
        return wrapper
    return decorator
