#!/usr/bin/env python3
"""
Script to import Cambodia location data from SQL file directly to SQLite.
"""
import sqlite3
import re
import os

def main():
    db_path = 'db.sqlite3'
    sql_path = 'docs/usp_location_data.sql'
    
    if not os.path.exists(sql_path):
        print(f'Error: {sql_path} not found')
        return
    
    print('Reading SQL file...')
    with open(sql_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace table names to match Django's table names
    content = content.replace('`provinces`', 'wallet_province')
    content = content.replace('`districts`', 'wallet_district')
    content = content.replace('`communes`', 'wallet_commune')
    content = content.replace('`villages`', 'wallet_village')
    
    # Remove SET statements
    content = re.sub(r'SET\s+.*?;', '', content, flags=re.DOTALL)
    content = re.sub(r'START\s+TRANSACTION\s*;', '', content, flags=re.DOTALL)
    
    # Remove id column from INSERT statements since it's auto-generated
    # Pattern: INSERT INTO table (id, col1, col2...) -> INSERT INTO table (col1, col2...)
    content = re.sub(
        r'INSERT\s+INTO\s+(\w+)\s*\(\s*id\s*,',
        r'INSERT INTO \1(',
        content
    )
    
    # For values, remove the first value (id) from each row
    # Pattern: (1, 'value', ...) -> ('value', ...)
    content = re.sub(
        r'\(\s*\d+\s*,',
        '(',
        content
    )
    
    print('Connecting to database...')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing data (optional)
    print('Clearing existing data...')
    cursor.execute('DELETE FROM wallet_village')
    cursor.execute('DELETE FROM wallet_commune')
    cursor.execute('DELETE FROM wallet_district')
    cursor.execute('DELETE FROM wallet_province')
    
    # Execute statements one by one
    statements = [s.strip() for s in content.split(';') if s.strip()]
    
    total = len(statements)
    for i, stmt in enumerate(statements):
        if stmt.startswith('INSERT'):
            try:
                cursor.execute(stmt)
                if (i + 1) % 100 == 0:
                    print(f'  Progress: {i + 1}/{total}')
            except Exception as e:
                print(f'  Error on statement {i+1}: {e}')
                print(f'    {stmt[:100]}...')
    
    conn.commit()
    
    # Show counts
    cursor.execute('SELECT COUNT(*) FROM wallet_province')
    print(f'Provinces: {cursor.fetchone()[0]}')
    
    cursor.execute('SELECT COUNT(*) FROM wallet_district')
    print(f'Districts: {cursor.fetchone()[0]}')
    
    cursor.execute('SELECT COUNT(*) FROM wallet_commune')
    print(f'Communes: {cursor.fetchone()[0]}')
    
    cursor.execute('SELECT COUNT(*) FROM wallet_village')
    print(f'Villages: {cursor.fetchone()[0]}')
    
    conn.close()
    print('Done!')

if __name__ == '__main__':
    main()
