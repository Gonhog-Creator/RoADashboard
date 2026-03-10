import streamlit as st
import requests
import pandas as pd
from io import StringIO
import os
from datetime import datetime, timedelta
import jwt
import hashlib
from functools import wraps

st.title("🔐 Debug - Loading Configuration")

# Debug: Show all available secrets
st.write("🔍 Debug: Checking secrets...")
try:
    all_secrets = dict(st.secrets)
    st.write("Available secrets:", list(all_secrets.keys()))
    
    if "secret_key" in st.secrets:
        st.write("✅ secret_key found")
        SECRET_KEY = st.secrets["secret_key"]
    else:
        st.error("❌ secret_key NOT found")
        st.stop()
    
    if "admin_users" in st.secrets:
        st.write("✅ admin_users found:", st.secrets["admin_users"])
        ADMIN_USERS = dict(st.secrets["admin_users"])
    else:
        st.error("❌ admin_users NOT found")
        st.stop()
    
    # Optional GitHub secrets
    GITHUB_TOKEN = st.secrets.get("github_token", "")
    CSV_REPO_URL = st.secrets.get("csv_repo_url", "")
    
    st.write(f"GitHub token: {'✅ Found' if GITHUB_TOKEN else '❌ Not found'}")
    st.write(f"CSV repo URL: {'✅ Found' if CSV_REPO_URL else '❌ Not found'}")
    
    st.success("✅ All secrets loaded successfully!")
    
except Exception as e:
    st.error(f"❌ Error loading secrets: {e}")
    st.write("Please check your Streamlit secrets configuration:")
    st.code("""
secret_key = "your_secret_key"

[admin_users]
username = "password_hash"

github_token = "github_pat_..."
csv_repo_url = "https://github.com/username/repo"
    """)
    st.stop()

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
    
    token = st.query_params.get('token') or st.session_state.get('token')
    
    if token and not st.session_state.authenticated:
        username = verify_token(token)
        if username:
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.token = token
            st.query_params.clear()
            return True
    
    return st.session_state.authenticated

def login_page():
    """Display login page"""
    st.title("🔐 Realm Analytics - Login")
    
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            if username in ADMIN_USERS and ADMIN_USERS[username] == hashed_password:
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

@require_auth
def main():
    show_logout_button()
    st.title("🏰 Realm Analytics Dashboard - Debug Mode")
    st.success("✅ Authentication working!")
    
    if GITHUB_TOKEN and CSV_REPO_URL:
        st.info("📡 Remote CSV configured")
    else:
        st.warning("⚠️ Remote CSV not configured")

if __name__ == "__main__":
    main()
