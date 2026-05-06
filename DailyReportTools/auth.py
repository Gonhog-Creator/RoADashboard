import streamlit as st
import hashlib
import os
import json
from datetime import datetime, timedelta, timezone
import jwt
from functools import wraps

# Configuration - Load from Streamlit secrets or local fallback
def load_secrets():
    """Load secrets from Streamlit Cloud or local fallback"""
    try:
        # Try Streamlit Cloud secrets first
        SECRET_KEY = st.secrets["secret_key"]
        ADMIN_USERS = dict(st.secrets["admin_users"])
        return SECRET_KEY, ADMIN_USERS, "cloud"
    except:
        try:
            # Fallback to local config file
            import os
            config_path = os.path.join(os.path.dirname(__file__), "local_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                SECRET_KEY = config["SECRET_KEY"]
                ADMIN_USERS = config["ADMIN_USERS"]
                return SECRET_KEY, ADMIN_USERS, "local"
            else:
                raise FileNotFoundError("local_config.json not found")
        except Exception as e:
            st.error("❌ Please configure secrets in Streamlit Community Cloud settings or create local_config.json")
            st.info("For local development, create local_config.json with:")
            st.code('''
{
  "SECRET_KEY": "your-secret-key-here",
  "ADMIN_USERS": {
    "admin": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
    "Gonhog": "2307f6b237dcc4de495b84c563d08b5cc362714c7699356a6a69f3994f51e6ae"
  }
}
            ''')
            st.stop()

SECRET_KEY, ADMIN_USERS, secrets_source = load_secrets()

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
        st.subheader("Database Mode")
        database_mode_index = st.radio(
            "Select database loading mode:",
            options=["Full Database", "Partial Database", "Local Database"],
            key="database_mode_selection",
            help="Full: Loads all data (slower)\nPartial: Loads recent data + 2 points per day (faster)\nLocal: Uses local files (fastest)"
        )
        
        # Convert selection to mode value
        if database_mode_index == "Full Database":
            database_mode = "full"
        elif database_mode_index == "Partial Database":
            database_mode = "partial"
        else:
            database_mode = "local"
        
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
                # Get database mode from the radio button widget
                selected_mode = st.session_state.get('database_mode_selection', 'Full Database')
                # Convert string selection to mode value
                if selected_mode == "Full Database":
                    mode_value = "full"
                elif selected_mode == "Partial Database":
                    mode_value = "partial"
                else:
                    mode_value = "local"
                st.session_state.database_mode = mode_value  # Store database selection
                st.success(f"Login successful! Database mode: {selected_mode}")
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
