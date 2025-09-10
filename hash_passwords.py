import getpass, streamlit_authenticator as stauth
print('Password Hasher')
while True:
 p=getpass.getpass('Enter password (blank to quit): ')
 if not p: break
 print('Hashed:', stauth.Hasher([p]).generate()[0])
