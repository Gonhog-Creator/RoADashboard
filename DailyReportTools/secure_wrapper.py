import streamlit as st
import requests
import pandas as pd
from io import StringIO
import os
from datetime import datetime, timedelta, timezone
import jwt
import hashlib
from functools import wraps

# Import authentication functions from auth module
try:
    from auth import generate_token, verify_token, check_authentication, login_page, require_auth, logout, show_logout_button, get_github_credentials
except ImportError:
    try:
        from DailyReportTools.auth import generate_token, verify_token, check_authentication, login_page, require_auth, logout, show_logout_button, get_github_credentials
    except ImportError:
        # Fallback - define minimal functions needed
        import streamlit as st
        import json
        import os
        def get_github_credentials():
            try:
                # Try st.secrets first
                if hasattr(st, 'secrets'):
                    github_token = st.secrets.get("github_token", "")
                    csv_repo_url = st.secrets.get("csv_repo_url", "")
                    if github_token and csv_repo_url:
                        return github_token, csv_repo_url
                
                # Fallback to local_config.json
                config_path = os.path.join(os.path.dirname(__file__), "local_config.json")
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    return config.get("GITHUB_TOKEN", ""), config.get("CSV_REPO_URL", "")
                
                return "", ""
            except:
                return "", ""

# Use the auth module's credential loading
try:
    GITHUB_TOKEN, CSV_REPO_URL = get_github_credentials()
except Exception as e:
    st.error(f"❌ Error loading GitHub credentials: {e}")
    st.stop()



def load_csv_from_github():
    """Load CSV files from private GitHub repository and save them as individual files"""
    if not GITHUB_TOKEN or not CSV_REPO_URL:
        st.sidebar.warning("GitHub token or repository URL not configured")
        return False
    
    try:
        # Extract owner and repo from URL
        if "/tree/" in CSV_REPO_URL:
            # Handle URL with branch path
            repo_parts = CSV_REPO_URL.split("/tree/")
            repo_base = repo_parts[0]
            branch = repo_parts[1] if len(repo_parts) > 1 else "main"
        else:
            # Handle simple repo URL
            repo_base = CSV_REPO_URL
            branch = "main"
        
        # Extract owner and repo name
        url_parts = repo_base.replace("https://github.com/", "").split("/")
        if len(url_parts) < 2:
            st.sidebar.error("Invalid repository URL format")
            return False
        
        owner, repo = url_parts[0], url_parts[1]
        
        # API URL for repository contents
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
        
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Streamlit-Dashboard"
        }
        
        st.sidebar.write(f"Checking repository: {owner}/{repo}")
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            try:
                files = response.json()
                
                # Check if we got a valid JSON response
                if isinstance(files, str):
                    st.sidebar.error(f"API returned string instead of JSON: {files[:100]}...")
                    return False
                
                # GitHub API might return an error object instead of a list
                if isinstance(files, dict):
                    if 'message' in files:
                        st.sidebar.error(f"GitHub API error: {files['message']}")
                        return False
                    else:
                        st.sidebar.error(f"Unexpected API response format: {files}")
                        return False
                
                if not isinstance(files, list):
                    st.sidebar.error(f"Unexpected API response format")
                    return False
                
                csv_files = [f for f in files if f.get('name', '').endswith('.csv')]
                
                st.sidebar.write(f"Found {len(csv_files)} CSV files")
                
                if not csv_files:
                    st.sidebar.warning("No CSV files found in remote repository")
                    return False
                
                # Ensure Daily Reports directory exists
                os.makedirs("Daily Reports", exist_ok=True)
                
                downloaded_count = 0
                for file_info in csv_files:
                    try:
                        # Download each CSV file directly
                        download_url = file_info.get('download_url')
                        if not download_url:
                            st.sidebar.error(f"No download URL for {file_info.get('name', 'unknown')}")
                            continue
                        
                        csv_response = requests.get(download_url, headers=headers)
                        
                        if csv_response.status_code == 200:
                            # Save file directly with original name and content
                            filename = file_info['name']
                            file_path = f"Daily Reports/{filename}"
                            
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(csv_response.text)
                            
                            downloaded_count += 1
                            st.sidebar.success(f"Downloaded {filename}")
                        else:
                            st.sidebar.error(f"Failed to download {file_info['name']}: {csv_response.status_code}")
                    except Exception as e:
                        st.sidebar.error(f"Error processing {file_info.get('name', 'unknown')}: {e}")
                
                if downloaded_count > 0:
                    st.sidebar.success(f"Successfully downloaded {downloaded_count} CSV files")
                    return True
                else:
                    st.sidebar.error("No files were successfully downloaded")
                    return False
                    
            except ValueError as e:
                st.sidebar.error(f"Failed to parse JSON response: {e}")
                st.sidebar.write(f"Raw response: {response.text[:200]}...")
                return False
        else:
            st.sidebar.error(f"GitHub API error: {response.status_code}")
            st.sidebar.write(f"Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        st.sidebar.error(f"Error loading remote CSV files: {e}")
        return False

def load_csv_files():
    """Load CSV files based on database mode selection"""
    # Get database mode from session state
    database_mode = st.session_state.get('database_mode', 'full')
    
        
    # Ensure database_mode is a string
    if database_mode is None or not isinstance(database_mode, str):
        database_mode = 'full'
    
    # Display current mode
    st.sidebar.info(f"Database Mode: {database_mode.title()}")
    
    # Load data based on database mode and store in session state
    from data_loader import load_csv_files_with_mode
    df, parsed_count = load_csv_files_with_mode(st, database_mode)
    
    if df is not None and not df.empty:
        st.session_state.dashboard_data = df
        st.session_state.database_loaded = True
    else:
        st.session_state.dashboard_data = pd.DataFrame()
        st.session_state.database_loaded = False

@require_auth
def main():
    # Handle authentication and data loading
    show_logout_button()
    
    # Add debugging info
    st.sidebar.markdown("### 🐛 Debug Mode")
    st.sidebar.markdown("Forcing cache clear and detailed logging")
    
    # Clear all caches to force fresh start
    if hasattr(st, 'cache_data'):
        st.cache_data.clear()
    if hasattr(st, 'session_state'):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
    
    # Close sidebar by default
    st.sidebar.markdown('<style>div[data-testid="stSidebar"] > div:first-child {display: none;}</style>', unsafe_allow_html=True)
    
    # Load data with smart fallback
    try:
        load_csv_files()
    except Exception as e:
        st.error(f"❌ Error loading CSV files: {e}")
        st.info("Please check GitHub credentials and repository access")
        return
    
    # Import and run the original dashboard
    try:
        st.write("🔍 Starting dashboard execution...")
        
        # Get the current directory and dashboard path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        dashboard_path = os.path.join(current_dir, 'dashboard.py')
        
        st.write(f"📁 Current directory: {current_dir}")
        st.write(f"📄 Dashboard path: {dashboard_path}")
        
        # Check if dashboard file exists
        if not os.path.exists(dashboard_path):
            st.error(f"❌ Dashboard file not found: {dashboard_path}")
            return
        
        # Change to the DailyReportTools directory to ensure relative paths work
        original_cwd = os.getcwd()
        os.chdir(current_dir)
        
        st.write("📖 Reading dashboard code...")
        # Read and execute the dashboard code
        with open(dashboard_path, 'r') as f:
            dashboard_code = f.read()
        
        st.write("⚡ Executing dashboard code...")
        # Execute the dashboard code in the current namespace
        exec(dashboard_code, globals())
        
        st.write("✅ Dashboard execution completed")
        
        # Restore original working directory
        os.chdir(original_cwd)
        
    except FileNotFoundError:
        st.error(f"Dashboard file not found at: {dashboard_path}")
        st.info("Please ensure dashboard.py is in the DailyReportTools directory")
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")
        st.info("Please check the dashboard.py file for any syntax errors")
        import traceback
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
