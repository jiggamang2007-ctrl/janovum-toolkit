"""Patch toolkit_login.html to show pending approval message.
Run ON VPS."""
import sys

LOGIN_HTML = '/root/janovum-toolkit/platform/templates/toolkit_login.html'
with open(LOGIN_HTML, 'r') as f:
    code = f.read()

if 'pending' in code and 'approval' in code.lower():
    print('Already patched')
    sys.exit(0)

# Fix signup handler to show pending message
old = """    if (data.error) {
      showToast('signupToast', data.error, 'error');
    } else {
      showToast('signupToast', 'Account created! Redirecting...', 'success');
      setTimeout(() => { window.location.href = '/toolkit/use'; }, 500);
    }"""

new = """    if (data.error) {
      showToast('signupToast', data.error, 'error');
    } else if (data.status === 'pending') {
      showToast('signupToast', data.message || 'Account created! Waiting for admin approval. You will get an email when approved.', 'success');
    } else {
      showToast('signupToast', 'Account created! Redirecting...', 'success');
      setTimeout(() => { window.location.href = '/toolkit/use'; }, 500);
    }"""

if old in code:
    code = code.replace(old, new)
else:
    print('WARNING: Could not find signup handler to update')

# Also fix login to show pending message
old_login = """    if (data.error) {
      showToast('loginToast', data.error, 'error');"""

new_login = """    if (data.status === 'pending') {
      showToast('loginToast', 'Your account is pending approval. You will receive an email when approved.', 'error');
    } else if (data.error) {
      showToast('loginToast', data.error, 'error');"""

if old_login in code:
    code = code.replace(old_login, new_login)

with open(LOGIN_HTML, 'w') as f:
    f.write(code)
print('PATCHED toolkit_login.html')
