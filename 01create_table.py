#!/usr/bin/env python3

"""Enable pgvector (if not already enabled) and create an appropriate table if it doesn't exist
"""

import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
SERVICE_URI = os.getenv("PG_SERVICE_URI")

try:
    with psycopg.connect(SERVICE_URI) as conn:
        with conn.cursor() as cur:
            # Check if vector extension exists
            cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');")
            extension_exists = cur.fetchone()[0]
            
            if not extension_exists:
                cur.execute('CREATE EXTENSION vector;')
                print("Vector extension created successfully.")
            else:
                print("Vector extension already exists.")

            # Check if the pictures table exists
            cur.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'pictures');")
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                cur.execute('CREATE TABLE pictures (filename text PRIMARY KEY, embedding vector(512));')
                print("Pictures table created successfully.")
            else:
                print("Pictures table already exists.")

except Exception as exc:
    print(f'{exc.__class__.__name__}: {exc}')
