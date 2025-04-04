import pandas as pd
import pyarrow.parquet as pq
import psycopg2
import sqlalchemy
from io import StringIO

# Database connection settings
DB_USER = "your_user"
DB_PASSWORD = "your_password"
DB_HOST = "your_host"
DB_PORT = "5432"
DB_NAME = "your_database"
TABLE_NAME = "your_table"
PRIMARY_KEYS = ["your_primary_key_column"]  # Adjust this based on your table schema

# Create SQLAlchemy engine
engine = sqlalchemy.create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def upsert_parquet_to_postgres(parquet_file, table_name, primary_keys, chunk_size=100000):
    """Upsert parquet data into PostgreSQL efficiently in chunks, handling column name issues."""
    
    try:
        parquet_file = pq.ParquetFile(parquet_file)
        
        with engine.begin() as conn:  # Auto-commit or rollback on failure
            with conn.connection.cursor() as cursor:  # Auto-close cursor

                for batch in parquet_file.iter_batches(batch_size=chunk_size):
                    df = batch.to_pandas()

                    # Convert DataFrame to CSV format for bulk insert
                    output = StringIO()
                    df.to_csv(output, sep="\t", index=False, header=False)
                    output.seek(0)

                    # Fast bulk insert using COPY FROM
                    cursor.copy_from(output, table_name, sep="\t", null="")

                    # **Fix: Enclose column names in double quotes**
                    col_names = ", ".join(f'"{col}"' for col in df.columns)
                    key_names = ", ".join(f'"{key}"' for key in primary_keys)
                    update_clause = ", ".join([f'"{col}" = EXCLUDED."{col}"' for col in df.columns if col not in primary_keys])

                    # Perform upsert
                    values_placeholder = ", ".join(["%s"] * len(df.columns))  # Placeholder for values

                    sql_query = f"""
                        INSERT INTO {table_name} ({col_names}) 
                        VALUES {', '.join(str(tuple(row)) for row in df.itertuples(index=False))}
                        ON CONFLICT ({key_names}) DO UPDATE SET {update_clause}
                    """
                    cursor.execute(sql_query)

    except Exception as e:
        print(f"Error occurred: {e}")  # Log error
        raise  # Re-raise exception after logging

# Example usage
parquet_file_path = "your_file.parquet"
upsert_parquet_to_postgres(parquet_file_path, TABLE_NAME, PRIMARY_KEYS)
