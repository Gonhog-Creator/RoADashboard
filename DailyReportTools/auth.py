import streamlit as st
import hashlib
import os
import json
from datetime import datetime, timedelta
import jwt
from functools import wraps

# Configuration - Load from Streamlit secrets
try:
    # For Streamlit Community Cloud
    SECRET_KEY = st.secrets["secret_key"]
    ADMIN_USERS = dict(st.secrets["admin_users"])
    
    # Debug: Show what we loaded (remove this after fixing)
    if st.experimental_get_query_params().get('debug') == ['true']:
        st.sidebar.write("✅ Secrets loaded successfully")
        st.sidebar.write(f"Users: {list(ADMIN_USERS.keys())}")
        
except Exception as e:
    # Fallback for local development
    st.sidebar.error(f"Error loading secrets: {e}")
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    
    # Load users from environment variable or use defaults
    def load_users():
        """Load user credentials from environment variable"""
        users_env = os.getenv("ADMIN_USERS")
        if users_env:
            try:
                return json.loads(users_env)
            except json.JSONDecodeError:
                st.error("Invalid ADMIN_USERS format. Using default users.")
        
        # Default users (for local development)
        return {
            "admin": hashlib.sha256("admin123".encode()).hexdigest(),
            "user": hashlib.sha256("user123".encode()).hexdigest()
        }
    
    ADMIN_USERS = load_users()
    if st.experimental_get_query_params().get('debug') == ['true']:
        st.sidebar.write("Using fallback configuration")

def generate_token(username):
    """Generate JWT token for authenticated user"""
    payload = {
        'username': username,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['username']
    except:
        return None

def check_authentication():
    """Check if user is authenticated"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
    
    # Check for token in URL or session
    token = st.query_params.get('token') or st.session_state.get('token')
    
    if token and not st.session_state.authenticated:
        username = verify_token(token)
        if username:
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.token = token
            # Clear token from URL
            st.query_params.clear()
            return True
    
    return st.session_state.authenticated

def login_page():
    """Display login page"""
    st.title("🔐 Realm Analytics - Login")
    
    # Debug info
    debug_mode = st.experimental_get_query_params().get('debug') == ['true']
    if debug_mode:
        with st.expander("🔍 Debug Info"):
            st.write(f"Available users: {list(ADMIN_USERS.keys())}")
            if 'admin' in ADMIN_USERS:
                st.write(f"Admin hash: {ADMIN_USERS['admin']}")
    
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if debug_mode:
                st.write(f"Attempting login for: {username}")
            
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            if debug_mode:
                st.write(f"Password hash: {hashed_password}")
                if username in ADMIN_USERS:
                    st.write(f"Expected hash: {ADMIN_USERS[username]}")
                    st.write(f"Hashes match: {hashed_password == ADMIN_USERS[username]}")
            
            if username in ADMIN_USERS and ADMIN_USERS[username] == hashed_password:
                # Generate and store token
                token = generate_token(username)
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.token = token
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")

def require_auth(f):
    """Decorator to require authentication for a function"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not check_authentication():
            login_page()
            return None
        return f(*args, **kwargs)
    return wrapper

def logout():
    """Logout user"""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.token = None
    st.rerun()

def show_logout_button():
    """Show logout button in sidebar"""
    if st.session_state.get('authenticated'):
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"**Logged in as:** {st.session_state.username}")
        if st.sidebar.button("Logout"):
            logout()
