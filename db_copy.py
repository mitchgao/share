import pandas as pd
from sqlalchemy import create_engine

# SQL Server connection (modify accordingly)
sql_server_conn_str = "mssql+pyodbc://username:password@server/database?driver=ODBC+Driver+17+for+SQL+Server"
sql_engine = create_engine(sql_server_conn_str)

# PostgreSQL connection (modify accordingly)
pg_conn_str = "postgresql+psycopg2://username:password@host:port/database"
pg_engine = create_engine(pg_conn_str)

# Table to transfer
table_name = "your_table"

# Read data in chunks from SQL Server and insert into PostgreSQL
chunk_size = 10000  # Adjust chunk size based on performance testing
with sql_engine.connect() as sql_conn:
    with pg_engine.connect() as pg_conn:
        # Read the table schema
        first_chunk = pd.read_sql(f"SELECT * FROM {table_name}", sql_conn, chunksize=chunk_size)
        
        for i, chunk in enumerate(first_chunk):
            chunk.to_sql(table_name, pg_conn, if_exists="append" if i > 0 else "replace", index=False)
            print(f"Inserted chunk {i+1}")

print("Table copied successfully!")
