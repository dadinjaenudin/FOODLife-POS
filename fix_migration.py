import sqlite3

# Connect to database
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Update django_migrations to mark migration as applied
cursor.execute("""
    UPDATE django_migrations 
    SET applied = datetime('now') 
    WHERE app = 'core' AND name = '0006_user_profile_photo'
""")

conn.commit()
conn.close()

print('Migration 0006_user_profile_photo marked as applied successfully!')
