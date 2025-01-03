#!/usr/bin/env python3

import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

def get_database_metrics():
    # Get the service URI from the environment variable
    service_uri = os.getenv("PG_SERVICE_URI")

    if not service_uri:
        raise Exception("PG_SERVICE_URI environment variable is not set.")

    try:
        # Connect to your PostgreSQL database using psycopg
        with psycopg.connect(service_uri) as conn:
            with conn.cursor() as cursor:
                # Total number of tables
                cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
                num_tables = cursor.fetchone()[0]

                # Total number of pictures (embeddings)
                cursor.execute("SELECT COUNT(*) FROM pictures;")
                num_pictures = cursor.fetchone()[0]

                # Average embedding vector length using vector_norm()
                cursor.execute("SELECT AVG(vector_norm(embedding)) FROM pictures;")  # Adjust if necessary
                avg_embedding_length = cursor.fetchone()[0]

                # Index information for pictures table
                cursor.execute("SELECT * FROM pg_indexes WHERE tablename = 'pictures';")
                index_info = cursor.fetchall()

                # Disk usage for pictures table
                cursor.execute("SELECT pg_size_pretty(pg_total_relation_size('pictures'));")
                disk_usage = cursor.fetchone()[0]

                # Installed extensions
                cursor.execute("SELECT * FROM pg_extension;")
                extensions = cursor.fetchall()

                # Print gathered metrics
                print(f"Total number of tables: {num_tables}")
                print(f"Total number of pictures: {num_pictures}")
                print(f"Average embedding vector length: {avg_embedding_length}")

                print("\nIndex Information:")
                for index in index_info:
                    print(f"Index Name: {index[2]}, Index Definition: {index[3]}")

                print(f"\nDisk Usage for 'pictures' table: {disk_usage}")

                print("\nInstalled Extensions:")
                for ext in extensions:
                    print(f"Name: {ext[0]}, Version: {ext[1]}, Description: {ext[3]}")

    except Exception as e:
        print(f"Error connecting to database: {e}")

if __name__ == "__main__":
    get_database_metrics()
