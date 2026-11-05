import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=RealDictCursor)

def execute_query(query, params=None, fetch=False):
    """Helper function to execute queries safely."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        result = cur.fetchall() if fetch else None
        
        # FIX: Commit regardless of fetch=True or False
        conn.commit() 
        return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
