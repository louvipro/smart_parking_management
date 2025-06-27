#!/usr/bin/env python3
"""Check database schema and tables"""
import sqlite3

# Connect to the database
conn = sqlite3.connect('parking.db')
cursor = conn.cursor()

print("=== DATABASE SCHEMA ===\n")

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables in database:")
for table in tables:
    print(f"- {table[0]}")

# Get schema for parking_sessions table
print("\n=== PARKING_SESSIONS TABLE SCHEMA ===")
cursor.execute("PRAGMA table_info(parking_sessions)")
columns = cursor.fetchall()
print("Columns:")
for col in columns:
    print(f"- {col[1]} ({col[2]}) {'NOT NULL' if col[3] else 'NULL OK'} {'[PRIMARY KEY]' if col[5] else ''}")

# Sample data from parking_sessions
print("\n=== SAMPLE DATA (All Records) ===")
cursor.execute("SELECT * FROM parking_sessions")
rows = cursor.fetchall()

# Get column names
cursor.execute("PRAGMA table_info(parking_sessions)")
column_info = cursor.fetchall()
column_names = [col[1] for col in column_info]

print(f"Columns: {', '.join(column_names)}")
print("-" * 80)
for row in rows:
    print(row)

conn.close()