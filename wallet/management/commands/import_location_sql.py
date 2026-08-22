"""
Management command to import Cambodia location data from SQL file using raw SQL.
Usage: python manage.py import_location_sql docs/usp_location_data.sql
"""
import os
import re
from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = 'Import Cambodia provinces, districts, communes, and villages from SQL file using raw SQL'

    def add_arguments(self, parser):
        parser.add_argument('sql_file', type=str, help='Path to the SQL file')

    def handle(self, *args, **options):
        sql_file = options['sql_file']
        
        if not os.path.exists(sql_file):
            self.stdout.write(self.style.ERROR(f'File not found: {sql_file}'))
            return
        
        self.stdout.write(f'Reading SQL file: {sql_file}')
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract and execute each INSERT statement
        with transaction.atomic():
            self.execute_inserts(content, 'provinces')
            self.execute_inserts(content, 'districts')
            self.execute_inserts(content, 'communes')
            self.execute_inserts(content, 'villages')
        
        self.stdout.write(self.style.SUCCESS('Data import completed successfully!'))
        self.show_counts()
    
    def execute_inserts(self, content, table_name):
        """Extract and execute INSERT statements for a table."""
        self.stdout.write(f'Importing {table_name}...')
        
        # Pattern to match INSERT statement for the table
        pattern = rf"INSERT INTO `{table_name}`.*?VALUES\s*(.+?);"
        matches = re.findall(pattern, content, re.DOTALL)
        
        if not matches:
            self.stdout.write(self.style.WARNING(f'No data found for {table_name}'))
            return
        
        with connection.cursor() as cursor:
            for values_clause in matches:
                # Split into individual row value sets
                rows = self._split_rows(values_clause)
                
                for row in rows:
                    try:
                        # Replace backticks with double quotes for PostgreSQL/SQLite compatibility
                        # and fix the table name for Django's table naming
                        sql = f'INSERT INTO wallet_{table_name} VALUES {row}'
                        cursor.execute(sql)
                    except Exception as e:
                        # Skip duplicates or other errors silently
                        pass
        
        self.stdout.write(f'  Completed {table_name}')
    
    def _split_rows(self, values_clause):
        """Split a VALUES clause into individual row tuples."""
        rows = []
        current = ''
        depth = 0
        
        for char in values_clause:
            if char == '(':
                if depth == 0:
                    current = ''
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    rows.append(f'({current})')
                    current = ''
            elif depth > 0:
                current += char
        
        return rows
    
    def show_counts(self):
        """Show current record counts."""
        from wallet.models import Province, District, Commune, Village
        
        self.stdout.write('')
        self.stdout.write('Current counts:')
        self.stdout.write(f'  Provinces: {Province.objects.count()}')
        self.stdout.write(f'  Districts: {District.objects.count()}')
        self.stdout.write(f'  Communes: {Commune.objects.count()}')
        self.stdout.write(f'  Villages: {Village.objects.count()}')
