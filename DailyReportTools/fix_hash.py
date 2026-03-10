import hashlib

def generate_hash(username, password):
    """Generate SHA256 hash for user"""
    return hashlib.sha256(password.encode()).hexdigest()

# Your current setup
print("🔐 Current TOML Setup:")
print('Gonhog = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"')
print("This hash is for password: admin123")
print()

# Generate correct hash for your actual password
your_password = input("Enter password for Gonhog: ")
correct_hash = generate_hash("Gonhog", your_password)

print(f"\n✅ Correct TOML entry:")
print(f'Gonhog = "{correct_hash}"')

# Also generate for Higgins if needed
higgins_password = input("\nEnter password for Higgins (or press Enter to skip): ")
if higgins_password:
    higgins_hash = generate_hash("Higgins", higgins_password)
    print(f'\nHiggins = "{higgins_hash}"')
