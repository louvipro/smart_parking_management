#!/usr/bin/env python3
"""Check parking database content using built-in sqlite3"""
import sqlite3
from datetime import datetime

# Connect to the database
conn = sqlite3.connect('parking.db')
cursor = conn.cursor()

print("=== PARKING DATABASE ANALYSIS ===\n")

# 1. Count active parking sessions (exit_time is NULL)
cursor.execute("SELECT COUNT(*) FROM parking_sessions WHERE exit_time IS NULL")
active_count = cursor.fetchone()[0]
print(f"1. Active parking sessions (exit_time is NULL): {active_count}")

# 2. Count completed sessions (exit_time is NOT NULL)
cursor.execute("SELECT COUNT(*) FROM parking_sessions WHERE exit_time IS NOT NULL")
completed_count = cursor.fetchone()[0]
print(f"2. Completed sessions (exit_time is NOT NULL): {completed_count}")

# 3. Show entry times of active sessions
print("\n3. Entry times of active sessions:")
cursor.execute("SELECT id, entry_time, hourly_rate FROM parking_sessions WHERE exit_time IS NULL ORDER BY entry_time")
active_sessions = cursor.fetchall()
if active_sessions:
    for session_id, entry_time, hourly_rate in active_sessions:
        print(f"   - Session ID {session_id}: Entry at {entry_time}, Rate: ${hourly_rate}/hour")
else:
    print("   No active sessions found")

# 4. Check sessions with amount_paid > 0
cursor.execute("SELECT COUNT(*) FROM parking_sessions WHERE amount_paid > 0")
paid_count = cursor.fetchone()[0]
print(f"\n4. Sessions with amount_paid > 0: {paid_count}")

# Show details of paid sessions
if paid_count > 0:
    print("\n   Details of paid sessions:")
    cursor.execute("SELECT id, entry_time, exit_time, amount_paid, payment_status FROM parking_sessions WHERE amount_paid > 0")
    paid_sessions = cursor.fetchall()
    for session_id, entry_time, exit_time, amount_paid, payment_status in paid_sessions:
        print(f"   - Session ID {session_id}: ${amount_paid:.2f} paid, Status: {payment_status}")
        print(f"     Entry: {entry_time}, Exit: {exit_time}")

# Additional analysis
print("\n=== ADDITIONAL STATISTICS ===")

# Total number of sessions
cursor.execute("SELECT COUNT(*) FROM parking_sessions")
total_sessions = cursor.fetchone()[0]
print(f"Total parking sessions: {total_sessions}")

# Payment status breakdown
cursor.execute("SELECT payment_status, COUNT(*) FROM parking_sessions GROUP BY payment_status")
status_breakdown = cursor.fetchall()
print("\nPayment status breakdown:")
for status, count in status_breakdown:
    print(f"   - {status}: {count} sessions")

# Average amount paid (excluding NULL and 0)
cursor.execute("SELECT AVG(amount_paid) FROM parking_sessions WHERE amount_paid > 0")
avg_paid = cursor.fetchone()[0]
if avg_paid:
    print(f"\nAverage amount paid (when > 0): ${avg_paid:.2f}")

# Close connection
conn.close()