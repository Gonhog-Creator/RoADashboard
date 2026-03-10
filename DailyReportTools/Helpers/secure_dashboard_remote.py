import streamlit as st
import requests
import pandas as pd
from io import StringIO
import os
from datetime import datetime, timedelta
import jwt
import hashlib
from functools import wraps

# Configuration - Load from Streamlit secrets
try:
    SECRET_KEY = st.secrets["secret_key"]
    ADMIN_USERS = dict(st.secrets["admin_users"])
    
    # Handle nested secrets (github_token and csv_repo_url might be in admin_users)
    all_secrets = dict(st.secrets)
    
    GITHUB_TOKEN = None
    CSV_REPO_URL = None
    
    # Try to get github_token from root level first, then from admin_users
    if "github_token" in all_secrets:
        GITHUB_TOKEN = st.secrets["github_token"]
    elif "github_token" in ADMIN_USERS:
        GITHUB_TOKEN = ADMIN_USERS["github_token"]
    
    # Try to get csv_repo_url from root level first, then from admin_users
    if "csv_repo_url" in all_secrets:
        CSV_REPO_URL = st.secrets["csv_repo_url"]
    elif "csv_repo_url" in ADMIN_USERS:
        CSV_REPO_URL = ADMIN_USERS["csv_repo_url"]
    
except Exception as e:
    st.error(f"❌ Please configure secrets in Streamlit Community Cloud settings!")
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

def load_csv_from_github():
    """Load CSV files from private GitHub repository"""
    if not GITHUB_TOKEN or not CSV_REPO_URL:
        st.warning("⚠️ Remote CSV not configured. Using local files.")
        return load_local_csv_files()
    
    try:
        # Get list of CSV files from repo
        api_url = CSV_REPO_URL.replace("github.com", "api.github.com/repos")
        api_url = api_url.replace("/tree/main", "/contents")
        
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            files = response.json()
            csv_files = [f for f in files if f['name'].endswith('.csv')]
            
            all_data = []
            for file_info in csv_files:
                # Download each CSV file
                download_url = f"https://raw.githubusercontent.com/{CSV_REPO_URL.split('/')[-2]}/{CSV_REPO_URL.split('/')[-1]}/main/{file_info['name']}"
                csv_response = requests.get(download_url)
                
                if csv_response.status_code == 200:
                    csv_data = csv_response.text
                    df = pd.read_csv(StringIO(csv_data))
                    if not df.empty:
                        # Add filename info
                        df['source_file'] = file_info['name']
                        all_data.append(df)
                        st.success(f"✅ Loaded {file_info['name']}")
                else:
                    st.error(f"❌ Failed to load {file_info['name']}")
            
            if all_data:
                return pd.concat(all_data, ignore_index=True)
            else:
                st.warning("⚠️ No CSV files found in remote repository")
                return pd.DataFrame()
        else:
            st.error(f"❌ Failed to access repository: {response.status_code}")
            return load_local_csv_files()
            
    except Exception as e:
        st.error(f"❌ Error loading remote CSV files: {e}")
        return load_local_csv_files()

def load_local_csv_files():
    """Load CSV files from local directory"""
    import glob
    csv_files = glob.glob("Daily Reports/*.csv")
    all_data = []
    
    for file_path in csv_files:
        try:
            filename = os.path.basename(file_path)
            date_str = filename.split("_")[3] + "_" + filename.split("_")[4].replace(".csv", "")
            date = datetime.strptime(date_str, "%Y-%m-%d_%H%M%S")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse sections (simplified for example)
            sections = content.split('\nSection;')
            realm_data = {'date': date, 'filename': filename}
            
            for section in sections:
                if 'Realm Summary' in section:
                    lines = section.strip().split('\n')
                    for line in lines:
                        if 'Realm Name' in line:
                            realm_data['realm_name'] = line.split(';')[1].strip('"')
                        elif 'Total Players' in line:
                            realm_data['total_players'] = int(line.split(';')[1])
            
            all_data.append(realm_data)
            
        except Exception as e:
            st.error(f"Error parsing {filename}: {e}")
    
    return pd.DataFrame(all_data)

def load_csv_files():
    """Smart loading: Try local first, fallback to remote if empty"""
    
    # Try local files first
    local_df = load_local_csv_files()
    
    if not local_df.empty:
        st.sidebar.success("💾 Using local CSV files")
        return local_df
    
    # Fallback to remote if local is empty
    if GITHUB_TOKEN and CSV_REPO_URL:
        st.sidebar.info("📡 Local files empty, loading from remote repository...")
        remote_df = load_csv_from_github()
        
        if not remote_df.empty:
            st.sidebar.success("✅ Using remote CSV files")
            return remote_df
        else:
            st.sidebar.error("❌ Remote files also empty")
    
    # No data available
    st.sidebar.error("❌ No CSV files available locally or remotely")
    return pd.DataFrame()

@require_auth
def main():
    show_logout_button()
    
    st.title("🏰 Realm Analytics Dashboard")
    
    # Smart data loading with fallback
    df = load_csv_files()
    
    if df.empty:
        st.error("❌ No data available!")
        st.info("💡 Please add CSV files to either:")
        st.info("• Local 'Daily Reports' folder")
        st.info("• Remote GitHub repository")
        return
    
    # Display data info
    st.sidebar.markdown("---")
    st.sidebar.write(f"📊 Records loaded: {len(df)}")
    if 'source_file' in df.columns:
        st.sidebar.write("📁 Source files:")
        for file in df['source_file'].unique():
            st.sidebar.write(f"• {file}")
    
    # Simple dashboard
    if not df.empty:
        st.subheader("📈 Total Players Over Time")
        if 'date' in df.columns:
            fig_data = df.sort_values('date')
            st.line_chart(fig_data.set_index('date')['total_players'])
        
        st.subheader("📋 Recent Data")
        st.dataframe(df.tail(10))
