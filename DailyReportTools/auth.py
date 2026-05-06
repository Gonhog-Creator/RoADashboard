import streamlit as st
import hashlib
import os
import json
from datetime import datetime, timedelta, timezone
import jwt
from functools import wraps

# Configuration - Load from Streamlit secrets (secure - not in GitHub)
try:
    # For Streamlit Community Cloud
    SECRET_KEY = st.secrets["secret_key"]
    ADMIN_USERS = dict(st.secrets["admin_users"])
    
except Exception as e:
    st.error(f"❌ Please configure secrets in Streamlit Community Cloud settings!")
    st.stop()

def generate_token(username):
    """Generate JWT token for authenticated user"""
    payload = {
        'username': username,
        'exp': datetime.now(timezone.utc) + timedelta(hours=24),
        'iat': datetime.now(timezone.utc)
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
    debug_mode = st.query_params.get("debug") == "true"
    if debug_mode:
        with st.expander("🔍 Debug Info"):
            st.write(f"Available users: {list(ADMIN_USERS.keys())}")
            if 'admin' in ADMIN_USERS:
                st.write(f"Admin hash: {ADMIN_USERS['admin']}")
    
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        # Database mode selection
        st.markdown("---")
        st.markdown("**Database Mode**")
        database_mode = st.radio(
            "Select Database Mode",
            options=["full", "partial", "local"],
            index=0,
            help="Full: Load all files from GitHub\nPartial: Load 2 files/day + last 24h\nLocal: Use cached files with sync",
            key="login_database_mode"
        )
        
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
                st.session_state.database_mode = database_mode
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
