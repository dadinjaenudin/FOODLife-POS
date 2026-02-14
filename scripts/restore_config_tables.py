"""
Restore POS configuration tables from a pg_dump backup file.

Usage:
    python scripts/restore_config_tables.py <backup_file.sql>
    python scripts/restore_config_tables.py  (auto-detects latest backup_before_reset_*.sql)

This script:
1. Extracts COPY blocks for config/master tables from the backup
2. Generates a restore SQL file
3. Runs it against the Docker PostgreSQL container via docker-compose

Tables restored (in dependency order):
  Prerequisites (FK parents):
  - auth_group                 (Auth Groups)
  - core_company               (Company)
  - core_brand                 (Brand)
  - core_store                 (Store)
  - core_storebrand            (Store-Brand mapping)
  - core_user                  (Users)
  - core_user_groups           (User-Group M2M)

  Config tables:
  - core_eft_terminal          (EFT Terminals)
  - core_media_group           (Media Groups)
  - core_payment_method_profile (Payment Profiles)
  - core_data_entry_prompt     (Data Entry Prompts for Payment Profiles)
  - core_posterminal           (POS Terminals)
  - core_posterminal_payment_profiles (Terminal <-> Profile M2M)
  - core_customerdisplayconfig (Display Configs)
  - core_customerdisplayslide  (Display Slides)
  - core_customerdisplaypromo  (Display Promos)
  - core_receipttemplate       (Receipt Templates)
  - kitchen_checkertemplate    (Checker Templates)
  - kitchen_kitchentickettemplate (Kitchen Templates)
"""

import re
import sys
import os
import glob
import subprocess
import tempfile

# --- Configuration ---
TABLES_TO_RESTORE = [
    # Order matters: parents before children (FK dependencies)

    # --- Prerequisites (FK parents) ---
    'auth_group',
    'core_company',
    'core_brand',
    'core_store',
    'core_storebrand',
    'core_user',
    'core_user_groups',

    # --- Config tables ---
    'core_eft_terminal',
    'core_media_group',
    'core_payment_method_profile',
    'core_data_entry_prompt',
    'core_posterminal',
    'core_posterminal_payment_profiles',
    'core_customerdisplayconfig',
    'core_customerdisplayslide',
    'core_customerdisplaypromo',
    'core_receipttemplate',
    'kitchen_checkertemplate',
    'kitchen_kitchentickettemplate',
]

DOCKER_CONTAINER = 'fnb_edge_db'
DB_NAME = 'fnb_edge_db'
DB_USER = 'postgres'


def find_latest_backup(project_dir):
    """Find the most recent backup_before_reset_*.sql file."""
    pattern = os.path.join(project_dir, 'backup_before_reset_*.sql')
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def extract_copy_blocks(backup_path, tables):
    """Extract COPY...\\. blocks for specified tables from pg_dump file."""
    with open(backup_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    blocks = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('COPY public.'):
            match = re.match(r'COPY public\.(\S+)\s', line)
            if match:
                table_name = match.group(1)
                if table_name in tables:
                    block_lines = [line]
                    i += 1
                    while i < len(lines) and lines[i].strip() != '\\.':
                        block_lines.append(lines[i])
                        i += 1
                    if i < len(lines):
                        block_lines.append(lines[i])  # The \. terminator
                    blocks[table_name] = block_lines
                    data_rows = len(block_lines) - 2
                    print(f'  Found {table_name}: {data_rows} rows')
        i += 1

    return blocks


def generate_restore_sql(blocks, tables):
    """Generate SQL with TRUNCATE + COPY statements."""
    sql_lines = []
    sql_lines.append('-- Auto-generated restore script for POS config tables\n')
    sql_lines.append('BEGIN;\n\n')

    # Truncate in reverse dependency order
    sql_lines.append('-- Truncate existing data (reverse dependency order)\n')
    for table in reversed(tables):
        if table in blocks:
            sql_lines.append(f'TRUNCATE TABLE public.{table} CASCADE;\n')
    sql_lines.append('\n')

    # COPY blocks in dependency order
    for table in tables:
        if table in blocks:
            sql_lines.append(f'-- Restore {table}\n')
            for line in blocks[table]:
                sql_lines.append(line)
            sql_lines.append('\n')

    sql_lines.append('COMMIT;\n')
    return ''.join(sql_lines)


def run_restore(sql_content):
    """Execute restore SQL via docker exec."""
    # Write SQL to temp file
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, encoding='utf-8')
    tmp.write(sql_content)
    tmp.close()

    try:
        print(f'\nRunning restore via docker exec {DOCKER_CONTAINER}...')

        cmd = [
            'docker', 'exec', '-i', DOCKER_CONTAINER,
            'psql', '-U', DB_USER, '-d', DB_NAME, '-v', 'ON_ERROR_STOP=1'
        ]

        result = subprocess.run(
            cmd,
            input=sql_content,
            capture_output=True,
            text=True,
            encoding='utf-8',
        )

        if result.returncode == 0:
            print('\nRestore completed successfully!')
            if result.stdout:
                # Count COPY lines
                copies = [l for l in result.stdout.splitlines() if l.startswith('COPY')]
                for c in copies:
                    print(f'  {c}')
        else:
            print(f'\nRestore FAILED (exit code {result.returncode})')
            if result.stderr:
                print(f'Error: {result.stderr}')
            return False

    finally:
        os.unlink(tmp.name)

    return True


def main():
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Determine backup file
    if len(sys.argv) > 1:
        backup_path = sys.argv[1]
    else:
        backup_path = find_latest_backup(project_dir)
        if not backup_path:
            print('ERROR: No backup file found. Provide path as argument.')
            print('Usage: python scripts/restore_config_tables.py <backup_file.sql>')
            sys.exit(1)

    if not os.path.exists(backup_path):
        print(f'ERROR: Backup file not found: {backup_path}')
        sys.exit(1)

    print(f'Backup file: {backup_path}')
    print(f'Extracting {len(TABLES_TO_RESTORE)} tables...\n')

    # Extract
    blocks = extract_copy_blocks(backup_path, TABLES_TO_RESTORE)

    missing = [t for t in TABLES_TO_RESTORE if t not in blocks]
    if missing:
        print(f'\nWARNING: Missing tables in backup: {missing}')

    if not blocks:
        print('ERROR: No matching tables found in backup.')
        sys.exit(1)

    # Generate SQL
    sql_content = generate_restore_sql(blocks, TABLES_TO_RESTORE)

    # Also save SQL file for reference
    sql_path = os.path.join(project_dir, 'restore_selected_tables.sql')
    with open(sql_path, 'w', encoding='utf-8') as f:
        f.write(sql_content)
    print(f'\nSQL saved to: {sql_path}')

    # Run restore
    success = run_restore(sql_content)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
