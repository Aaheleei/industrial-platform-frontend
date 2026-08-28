import psycopg2

DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "Aahelee"
DB_HOST = "localhost"
DB_PORT = "5432"

def get_db_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Updated table to support sequential time-series history tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prediction_logs (
            id SERIAL PRIMARY KEY,
            sensor_data TEXT NOT NULL,
            sequence_trend_score FLOAT DEFAULT 0.0,
            quality_estimation FLOAT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("Database table 'prediction_logs' with time-series intelligence initialized successfully!")

if __name__ == "__main__":
    init_db()