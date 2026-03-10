#!/usr/bin/env python3
"""
Generate user credentials for Streamlit Community Cloud deployment
Run this locally to generate your password hashes
"""

import hashlib
import secrets

def generate_password_hash(password):
    """Generate SHA256 hash for password"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_secret_key():
    """Generate a random secret key"""
    return secrets.token_urlsafe(32)

# Replace these with your actual usernames and passwords
users_config = {
    "admin": "admin123",  # Change this!
    "user": "user123"     # Change this!
}

# Generate hashes
users_hashed = {}
for username, password in users_config.items():
    users_hashed[username] = generate_password_hash(password)

secret_key = generate_secret_key()

print("🔑 Streamlit Community Cloud Configuration")
print("=" * 50)
print("\n1. Go to your Streamlit app → Settings → Advanced settings")
print("2. Add these secrets in TOML format:")
print()

print(f'secret_key = "{secret_key}"')
print()
print("[admin_users]")
for username, password_hash in users_hashed.items():
    print(f'{username} = "{password_hash}"')

print()
print("3. Change your main module to: DailyReportTools/secure_dashboard.py")
print("4. Save and redeploy")
print()
print("🔐 Login credentials:")
for username, password in users_config.items():
    print(f"   Username: {username}")
    print(f"   Password: {password}")
print()
print("⚠️  IMPORTANT: Change the default passwords above!")
