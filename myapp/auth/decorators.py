from flask import current_app, redirect, url_for, flash, make_response
from flask_login import current_user
from functools import wraps

def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Login required", "warning")
                current_app.logger.info(f"Access denied: User not authenticated")
                return redirect(url_for('auth.login'))

            if current_user.role not in roles:
                flash("Access denied: insufficient permissions", "warning")
                current_app.logger.info(f"Access denied: insufficient permission for {current_user.username}")
                return redirect(url_for('main.home'))

            return view_func(*args, **kwargs)
        return wrapper
    return decorator

def no_cache(view):
    @wraps(view)
    def no_cache_wrapper(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    return no_cache_wrapper