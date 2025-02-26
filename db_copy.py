import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine, text

# Database connection parameters
DB_USER = "your_user"
DB_PASSWORD = "your_password"
DB_HOST = "your_host"
DB_PORT = "5432"
DB_NAME = "your_database"
TABLE_NAME = "your_table"
PRIMARY_KEYS = ["your_primary_key_column"]  # Change this to your actual primary keys

# Create database connection
engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def upsert_parquet_to_postgres(parquet_file, table_name, primary_keys, chunk_size=100000):
    """ Upsert parquet file data into PostgreSQL efficiently """
    with engine.begin() as conn:  # Use transaction for atomicity
        for chunk in pd.read_parquet(parquet_file, chunksize=chunk_size):
            # Generate ON CONFLICT SQL clause dynamically
            update_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in chunk.columns if col not in primary_keys])
            conflict_clause = f"ON CONFLICT ({', '.join(primary_keys)}) DO UPDATE SET {update_clause}"
            
            # Upload data using Pandas' to_sql() with raw SQL
            chunk.to_sql(table_name, conn, if_exists="append", index=False, method="multi")
            
            # Apply ON CONFLICT manually via SQL
            conn.execute(text(f"""
                INSERT INTO {table_name} ({', '.join(chunk.columns)}) 
                VALUES {', '.join(str(tuple(row)) for row in chunk.itertuples(index=False))}
                {conflict_clause}
            """))

# Example usage
parquet_file_path = "your_file.parquet"
upsert_parquet_to_postgres(parquet_file_path, TABLE_NAME, PRIMARY_KEYS)
