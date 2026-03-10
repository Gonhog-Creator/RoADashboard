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

# Debug: Show all available secrets in detail
st.write("🔍 Debug: Checking secrets...")
try:
    all_secrets = dict(st.secrets)
    st.write("Available secrets:", list(all_secrets.keys()))
    
    # Show the raw secrets structure
    st.write("Raw secrets structure:")
    st.json(all_secrets)
    
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
    
    # Check for GitHub secrets at root level
    GITHUB_TOKEN = None
    CSV_REPO_URL = None
    
    if "github_token" in all_secrets:
        GITHUB_TOKEN = st.secrets["github_token"]
        st.write("✅ github_token found at root level")
    elif "github_token" in ADMIN_USERS:
        st.write("⚠️ github_token found in admin_users (wrong location)")
        GITHUB_TOKEN = ADMIN_USERS["github_token"]
    else:
        st.write("❌ github_token NOT found anywhere")
    
    if "csv_repo_url" in all_secrets:
        CSV_REPO_URL = st.secrets["csv_repo_url"]
        st.write("✅ csv_repo_url found at root level")
    elif "csv_repo_url" in ADMIN_USERS:
        st.write("⚠️ csv_repo_url found in admin_users (wrong location)")
        CSV_REPO_URL = ADMIN_USERS["csv_repo_url"]
    else:
        st.write("❌ csv_repo_url NOT found anywhere")
    
    st.write(f"Final GitHub token: {'✅ Found' if GITHUB_TOKEN else '❌ Not found'}")
    st.write(f"Final CSV repo URL: {'✅ Found' if CSV_REPO_URL else '❌ Not found'}")
    
    if GITHUB_TOKEN and CSV_REPO_URL:
        st.success("✅ All secrets loaded successfully!")
    else:
        st.warning("⚠️ Some secrets missing")
    
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
    
    # Show the final values that will be used
    if GITHUB_TOKEN and CSV_REPO_URL:
        st.info("📡 Remote CSV configured")
        st.write(f"Repository: {CSV_REPO_URL}")
        st.write(f"Token starts with: {GITHUB_TOKEN[:10]}...")
    else:
        st.warning("⚠️ Remote CSV not configured")
        if not GITHUB_TOKEN:
            st.error("❌ GitHub token missing")
        if not CSV_REPO_URL:
            st.error("❌ CSV repository URL missing")

if __name__ == "__main__":
    main()
