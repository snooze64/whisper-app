#!/usr/bin/env python3
"""
Script to add await to test_db.commit() and test_db.refresh() calls
"""
import re
import sys
from pathlib import Path


def fix_db_calls(file_path):
    """Fix database calls to add await"""
    with open(file_path, 'r') as f:
        content = f.read()

    # Add await to test_db.commit()
    content = re.sub(
        r'(\s+)test_db\.commit\(\)',
        r'\1await test_db.commit()',
        content
    )

    # Add await to test_db.refresh()
    content = re.sub(
        r'(\s+)test_db\.refresh\(([\w,\s]+)\)',
        r'\1await test_db.refresh(\2)',
        content
    )

    # Add await to test_db.flush()
    content = re.sub(
        r'(\s+)test_db\.flush\(\)',
        r'\1await test_db.flush()',
        content
    )

    # Fix double await (in case it already had await)
    content = re.sub(
        r'await await test_db\.',
        r'await test_db.',
        content
    )

    with open(file_path, 'w') as f:
        f.write(content)

    print(f'Fixed: {file_path}')


def main():
    """Main function"""
    # Get all test files
    test_dir = Path(__file__).parent
    test_files = list(test_dir.glob('test_*.py'))

    # Exclude scripts
    test_files = [f for f in test_files if 'convert' not in f.name and 'fix' not in f.name]

    for test_file in test_files:
        try:
            fix_db_calls(test_file)
        except Exception as e:
            print(f'Error fixing {test_file}: {e}', file=sys.stderr)


if __name__ == '__main__':
    main()
