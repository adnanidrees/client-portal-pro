# Generate bcrypt hashes for users.yaml
import getpass, bcrypt
print("Password Hasher (bcrypt)")
while True:
    pwd = getpass.getpass("Enter password (blank to quit): ")
    if not pwd:
        break
    h = bcrypt.hashpw(pwd.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    print("Hashed:", h)
