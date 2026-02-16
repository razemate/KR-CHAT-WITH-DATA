import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SOURCE_DB_URL = os.getenv("SUPABASE_CONNECTION_STRING")
DEST_DB_URL = os.getenv("DATABASE_URL")

TABLES_TO_COPY = [
    "woo_subscriptions",
    "wc_webhooks",
    "woocommerce_api_keys"
]

def get_engine(url):
    try:
        # SQLAlchemy requires the driver to be specified for postgresql
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://")
        return create_engine(url)
    except Exception as e:
        print(f"Error creating engine for {url}: {e}")
        sys.exit(1)

def copy_table(source_engine, dest_engine, table_name):
    print(f"Processing table: {table_name}")
    try:
        # Check if table exists in source
        query = text(f"SELECT to_regclass(:table_name)")
        with source_engine.connect() as conn:
            result = conn.execute(query, {"table_name": table_name}).scalar()
            if not result:
                print(f"  - Table {table_name} does not exist in source. Skipping.")
                return

        # Read from source
        print(f"  - Reading from source...")
        df = pd.read_sql_table(table_name, source_engine)
        
        if df.empty:
            print(f"  - Table {table_name} is empty. Skipping data copy.")
            return
            
        print(f"  - Found {len(df)} rows.")

        # Write to destination
        print(f"  - Writing to destination...")
        df.to_sql(table_name, dest_engine, if_exists='replace', index=False)
        print(f"  - Successfully copied {table_name}.")
        
    except Exception as e:
        print(f"  - Error copying table {table_name}: {e}")

def copy_cron_jobs(source_engine, dest_engine):
    print("Processing cron jobs...")
    try:
        # Check if cron extension and table exist in source
        with source_engine.connect() as conn:
            # Check schema
            result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'cron'")).scalar()
            if not result:
                print("  - 'cron' schema not found in source. Skipping cron jobs.")
                return
                
            # Read jobs
            print("  - Reading cron jobs from source...")
            # We select specific columns to avoid issues with internal IDs if possible, 
            # or just copy everything and let the destination handle it (might conflict if IDs clash with existing).
            # Usually better to exclude 'jobid' if it's serial.
            df = pd.read_sql_query("SELECT schedule, command, nodename, nodeport, database, username, active, jobname FROM cron.job", conn)
            
        if df.empty:
            print("  - No cron jobs found.")
            return
            
        print(f"  - Found {len(df)} cron jobs.")
        
        # Write to destination
        # We need to ensure 'cron' extension is enabled in destination
        with dest_engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_cron"))
            conn.commit()
            
            # We can't use to_sql directly for cron.job because it's a special table?
            # Or maybe we can? 
            # Ideally we should use `cron.schedule` function to add jobs, but direct insert might work if we have permissions.
            # But `jobid` is auto-generated.
            # We should iterate and schedule them.
            
            print("  - Scheduling jobs in destination...")
            for index, row in df.iterrows():
                # Construct schedule command
                # SELECT cron.schedule(jobname, schedule, command)
                jobname = row.get('jobname')
                schedule = row.get('schedule')
                command = row.get('command')
                
                if jobname:
                    sql = text("SELECT cron.schedule(:jobname, :schedule, :command)")
                    conn.execute(sql, {"jobname": jobname, "schedule": schedule, "command": command})
                else:
                    sql = text("SELECT cron.schedule(:schedule, :command)")
                    conn.execute(sql, {"schedule": schedule, "command": command})
                
            conn.commit()
            print("  - Successfully scheduled cron jobs.")

    except Exception as e:
        print(f"  - Error copying cron jobs: {e}")

def main():
    if not SOURCE_DB_URL or not DEST_DB_URL:
        print("Error: Missing SUPABASE_CONNECTION_STRING or DATABASE_URL in environment variables.")
        return

    print("Connecting to databases...")
    source_engine = get_engine(SOURCE_DB_URL)
    dest_engine = get_engine(DEST_DB_URL)
    
    print("Starting migration...")
    
    # Copy tables
    for table in TABLES_TO_COPY:
        copy_table(source_engine, dest_engine, table)
        
    # Copy cron jobs
    copy_cron_jobs(source_engine, dest_engine)
    
    print("Migration completed.")

if __name__ == "__main__":
    main()
