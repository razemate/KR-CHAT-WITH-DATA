import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn_str = os.getenv("SUPABASE_CONNECTION_STRING")

try:
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    
    # Query to list all tables
    cur.execute("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        ORDER BY table_schema, table_name;
    """)
    
    tables = cur.fetchall()
    print("Tables in Supabase:")
    for schema, name in tables:
        print(f"{schema}.{name}")
        
    cur.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
