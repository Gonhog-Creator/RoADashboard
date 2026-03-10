import hashlib
import secrets

def generate_password_hash(password):
    """Generate SHA256 hash for password"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_secret_key():
    """Generate a random secret key"""
    return secrets.token_urlsafe(32)

print("🔐 Generate Secure Streamlit Secrets")
print("=" * 50)
print()

# Generate secret key
secret_key = generate_secret_key()
print(f"🔑 SECRET_KEY:")
print(f'secret_key = "{secret_key}"')
print()

# Get user credentials
print("👥 Enter user credentials (press Enter with empty username to finish):")
users = {}
while True:
    username = input("\nUsername: ").strip()
    if not username:
        break
        
    password = input("Password: ").strip()
    if not password:
        print("Password cannot be empty!")
        continue
        
    hash_password = generate_password_hash(password)
    users[username] = hash_password
    print(f"✅ Added user: {username}")

if users:
    print(f"\n📝 [admin_users] section:")
    print("[admin_users]")
    for username, password_hash in users.items():
        print(f'{username} = "{password_hash}"')
    
    print(f"\n🚀 Complete TOML for Streamlit Secrets:")
    print(f'secret_key = "{secret_key}"')
    print()
    print("[admin_users]")
    for username, password_hash in users.items():
        print(f'{username} = "{password_hash}"')
    
    print(f"\n✨ Copy the TOML above to your Streamlit app → Settings → Advanced settings")
else:
    print("\n❌ No users added. Please run again to add users.")
