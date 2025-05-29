import psycopg2
import os
from dotenv import load_dotenv

def initialize_database():
    """
    Initializes the PostgreSQL database and creates the 'conversations' table
    if it doesn't already exist, using environment variables for connection.
    """
    conn = None
    try:
        # Load database connection parameters from environment variables
        db_host = os.getenv("DB_HOST")
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_name = os.getenv("DB_NAME")
        db_port = os.getenv("DB_PORT", "5432") # Default to 5432 if not set

        # Check if all necessary environment variables are set
        if not all([db_host, db_user, db_password, db_name, db_port]):
            print("❌ Error: Missing one or more database environment variables (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT).")
            print("Please ensure they are set in your .env file or system environment.")
            return

        print(f"Attempting to connect to PostgreSQL: User={db_user}, DB={db_name}, Host={db_host}, Port={db_port}")

        # Establish connection to PostgreSQL
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        
        # Open a cursor to perform database operations
        with conn.cursor() as cur:
            # The schema for conversations table from the original subtask was:
            # customer_id TEXT NOT NULL,
            # conversation_time TIMESTAMP NOT NULL,
            # summary TEXT NOT NULL
            # Adding a primary key is good practice.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY, 
                    customer_id TEXT NOT NULL,
                    conversation_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    summary TEXT NOT NULL
                )
            """)
            # Changes made:
            # - Added 'id SERIAL PRIMARY KEY' for a unique auto-incrementing ID.
            # - Changed 'TIMESTAMP' to 'TIMESTAMP WITH TIME ZONE' for better timezone handling.
            # - Added 'DEFAULT CURRENT_TIMESTAMP' to 'conversation_time'.

            conn.commit()
        
        print(f"✅ Database '{db_name}' initialized and 'conversations' table ensured successfully on host '{db_host}'.")

    except psycopg2.OperationalError as e:
        print(f"❌ PostgreSQL Operational Error: {e}")
        print("   Please check if the PostgreSQL server is running, accessible,")
        print("   and if the database credentials (host, port, user, password, dbname) are correct.")
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL Error: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("🔌 PostgreSQL connection closed.")

if __name__ == "__main__":
    print("🚀 Starting database initialization script for PostgreSQL...")
    # Load environment variables from .env file
    # This is crucial if running this script directly and .env contains the DB credentials
    load_dotenv() 
    initialize_database()
    print("🏁 Database initialization script finished.")
