#!/usr/bin/env python3
path = '/root/janovum-toolkit/platform/server_v2.py'
with open(path) as f:
    content = f.read()

# Fix the broken f-string that has a literal newline inside it
# Replace the whole ETag inject line with a safe version
bad = "html.replace('<head>', f'<head>\n  <meta name=app-version content={etag}>', 1)"
good = "html.replace('<head>', '<head>\\n  <meta name=\"app-version\" content=\"' + etag + '\">', 1)"

if bad in content:
    content = content.replace(bad, good)
    with open(path, 'w') as f:
        f.write(content)
    print('Fixed f-string syntax error')
else:
    print('Not found, showing context:')
    idx = content.find('html.replace')
    print(repr(content[max(0,idx-20):idx+150]))
