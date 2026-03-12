import psycopg2
import re
import os

# Read .env file with UTF-8 encoding
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

url = os.environ.get('DATABASE_URL', '')
m = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', url)
conn = psycopg2.connect(host=m.group(3), port=int(m.group(4)), database=m.group(5), user=m.group(1), password=m.group(2))
cur = conn.cursor()

cur.execute('SELECT username, role, status FROM users')
rows = cur.fetchall()

print('Users in database:')
for r in rows:
    print(f'  {r[0]}: role={r[1]}, status={r[2]}')

cur.close()
conn.close()
