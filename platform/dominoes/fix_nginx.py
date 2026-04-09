"""Fix nginx config on VPS to add dominoes routes."""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('104.238.133.244', username='root', password='Ek2+X-HhF5-g{EJ7')

# First, write the nginx snippet file
nginx_snippet = """
    # Cuban Dominoes Game
    location /dominoes {
        return 301 /dominoes/;
    }
    location /dominoes/ {
        proxy_pass http://127.0.0.1:5052/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    location /domino-ws/ {
        proxy_pass http://127.0.0.1:5053/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }

"""

sftp = ssh.open_sftp()
with sftp.open('/tmp/dominoes_nginx.conf', 'w') as f:
    f.write(nginx_snippet)

# Write a python script to run ON the server
inserter = '''
with open("/etc/nginx/sites-enabled/janovum") as f:
    content = f.read()

# Remove any existing dominoes blocks (cleanup)
import re
content = re.sub(r'\\n\\s*# Cuban Dominoes Game.*?proxy_read_timeout 86400;\\s*\\}\\s*\\n', '\\n', content, flags=re.DOTALL)

with open("/tmp/dominoes_nginx.conf") as f:
    snippet = f.read()

# Insert before "listen 443 ssl;"
content = content.replace("    listen 443 ssl;", snippet + "    listen 443 ssl;")

with open("/etc/nginx/sites-enabled/janovum", "w") as f:
    f.write(content)
print("Config updated")
'''

with sftp.open('/tmp/insert_dominoes.py', 'w') as f:
    f.write(inserter)
sftp.close()

# Run the inserter
stdin, stdout, stderr = ssh.exec_command('python3 /tmp/insert_dominoes.py')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("Error:", err)

# Test nginx
stdin, stdout, stderr = ssh.exec_command('nginx -t 2>&1')
result = stderr.read().decode()
print("Nginx test:", result)

if 'successful' in result:
    ssh.exec_command('systemctl reload nginx')
    time.sleep(1)
    print("Nginx reloaded successfully!")
else:
    print("Config error! Showing relevant section:")
    stdin, stdout, stderr = ssh.exec_command('sed -n "155,185p" /etc/nginx/sites-enabled/janovum')
    print(stdout.read().decode())

ssh.close()
