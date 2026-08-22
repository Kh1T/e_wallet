"""
Management command to import Cambodia location data from SQL file.
Usage: python manage.py import_location_data docs/usp_location_data.sql
"""
import re
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from wallet.models import Province, District, Commune, Village


class Command(BaseCommand):
    help = 'Import Cambodia provinces, districts, communes, and villages from SQL file'

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
        
        # Parse and insert data in order: provinces -> districts -> communes -> villages
        with transaction.atomic():
            self.import_provinces(content)
            self.import_districts(content)
            self.import_communes(content)
            self.import_villages(content)
        
        self.stdout.write(self.style.SUCCESS('Data import completed successfully!'))
    
    def import_provinces(self, content):
        """Parse and import provinces."""
        self.stdout.write('Importing provinces...')
        
        # Extract province data
        pattern = r"INSERT INTO `provinces`.*?VALUES\s*\((.*?)\);"
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            self.stdout.write(self.style.WARNING('No province data found'))
            return
        
        data = match.group(1)
        rows = self._parse_rows(data)
        
        count = 0
        for row in rows:
            try:
                Province.objects.update_or_create(
                    id=int(row[0]),
                    defaults={
                        'code': row[1],
                        'name': row[2],
                        'name_other': row[3] if row[3] else None,
                        'is_active': bool(int(row[6])),
                    }
                )
                count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error importing province {row}: {e}'))
        
        self.stdout.write(f'  Imported {count} provinces')
    
    def import_districts(self, content):
        """Parse and import districts."""
        self.stdout.write('Importing districts...')
        
        pattern = r"INSERT INTO `districts`.*?VALUES\s*\((.*?)\);"
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            self.stdout.write(self.style.WARNING('No district data found'))
            return
        
        data = match.group(1)
        rows = self._parse_rows(data)
        
        count = 0
        for row in rows:
            try:
                District.objects.update_or_create(
                    id=int(row[0]),
                    defaults={
                        'province_id': int(row[1]),
                        'code': row[2],
                        'name': row[3],
                        'name_other': row[4] if row[4] else None,
                        'is_active': bool(int(row[7])),
                    }
                )
                count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error importing district {row}: {e}'))
        
        self.stdout.write(f'  Imported {count} districts')
    
    def import_communes(self, content):
        """Parse and import communes."""
        self.stdout.write('Importing communes...')
        
        pattern = r"INSERT INTO `communes`.*?VALUES\s*\((.*?)\);"
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            self.stdout.write(self.style.WARNING('No commune data found'))
            return
        
        data = match.group(1)
        rows = self._parse_rows(data)
        
        count = 0
        for row in rows:
            try:
                Commune.objects.update_or_create(
                    id=int(row[0]),
                    defaults={
                        'district_id': int(row[1]),
                        'code': row[2],
                        'name': row[3],
                        'name_other': row[4] if row[4] else None,
                        'is_active': bool(int(row[7])),
                    }
                )
                count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error importing commune {row}: {e}'))
        
        self.stdout.write(f'  Imported {count} communes')
    
    def import_villages(self, content):
        """Parse and import villages."""
        self.stdout.write('Importing villages...')
        
        pattern = r"INSERT INTO `villages`.*?VALUES\s*\((.*?)\);"
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            self.stdout.write(self.style.WARNING('No village data found'))
            return
        
        data = match.group(1)
        rows = self._parse_rows(data)
        
        count = 0
        for row in rows:
            try:
                Village.objects.update_or_create(
                    id=int(row[0]),
                    defaults={
                        'commune_id': int(row[1]),
                        'code': row[2],
                        'name': row[3],
                        'name_other': row[4] if row[4] else None,
                        'is_active': bool(int(row[7])),
                    }
                )
                count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error importing village {row}: {e}'))
        
        self.stdout.write(f'  Imported {count} villages')
    
    def _parse_rows(self, data):
        """Parse SQL rows from a VALUES clause."""
        rows = []
        current_row = []
        current_value = ''
        in_string = False
        string_char = None
        
        i = 0
        while i < len(data):
            char = data[i]
            
            if not in_string:
                if char in "'\"":
                    in_string = True
                    string_char = char
                    i += 1
                    continue
                elif char == '(':
                    current_row = []
                    current_value = ''
                elif char == ')':
                    if current_value.strip():
                        current_row.append(self._convert_value(current_value.strip()))
                    if current_row:
                        rows.append(current_row)
                    current_row = []
                    current_value = ''
                elif char == ',':
                    current_row.append(self._convert_value(current_value.strip()))
                    current_value = ''
                elif not char.isspace() or current_value:
                    current_value += char
            else:
                if char == string_char:
                    # Check for escaped quote
                    if i + 1 < len(data) and data[i + 1] == string_char:
                        current_value += char
                        i += 1
                    else:
                        in_string = False
                        string_char = None
                elif char == '\\':
                    # Handle escape sequences
                    if i + 1 < len(data):
                        next_char = data[i + 1]
                        if next_char in "'\"nrt\\":
                            if next_char == 'n':
                                current_value += '\n'
                            elif next_char == 'r':
                                current_value += '\r'
                            elif next_char == 't':
                                current_value += '\t'
                            else:
                                current_value += next_char
                            i += 1
                        else:
                            current_value += char
                    else:
                        current_value += char
                else:
                    current_value += char
            
            i += 1
        
        return rows
    
    def _convert_value(self, value):
        """Convert SQL value to Python value."""
        if value.upper() == 'NULL':
            return None
        
        # Remove surrounding quotes if present
        if (value.startswith("'") and value.endswith("'")) or \
           (value.startswith('"') and value.endswith('"')):
            return value[1:-1]
        
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        return value
