#!/usr/bin/env python3
"""
Script to convert synchronous tests to asynchronous tests
"""
import re
import sys
from pathlib import Path


def convert_test_file(file_path):
    """Convert a test file from sync to async"""
    with open(file_path, 'r') as f:
        content = f.read()

    # Add asyncio marker import if not present
    if '@pytest.mark.asyncio' not in content and 'async def test_' in content:
        # Already has some async tests, skip
        return

    # Pattern to match test function definitions
    pattern = r'^([@\w\s.()]*\n)?def (test_\w+)\((.*?)\):'

    def replace_func(match):
        decorators = match.group(1) or ''
        func_name = match.group(2)
        params = match.group(3)

        # Add asyncio marker
        if '@pytest.mark.asyncio' not in decorators:
            if decorators:
                decorators = decorators.rstrip('\n') + '\n@pytest.mark.asyncio\n'
            else:
                decorators = '@pytest.mark.asyncio\n'

        return f'{decorators}async def {func_name}({params}):'

    # Replace function definitions
    content = re.sub(pattern, replace_func, content, flags=re.MULTILINE)

    # Replace test_client method calls with await
    content = re.sub(
        r'(\s+)response = test_client\.(get|post|put|patch|delete)\(',
        r'\1response = await test_client.\2(',
        content
    )

    # Replace test_client calls in other patterns
    content = re.sub(
        r'(\s+)response = (\w+_)?client\.(get|post|put|patch|delete)\(',
        r'\1response = await \2client.\3(',
        content
    )

    with open(file_path, 'w') as f:
        f.write(content)

    print(f'Converted: {file_path}')


def main():
    """Main function"""
    # Get all test files
    test_dir = Path(__file__).parent
    test_files = list(test_dir.glob('test_*.py'))

    # Exclude this script
    test_files = [f for f in test_files if f.name != 'convert_tests_to_async.py']

    for test_file in test_files:
        try:
            convert_test_file(test_file)
        except Exception as e:
            print(f'Error converting {test_file}: {e}', file=sys.stderr)


if __name__ == '__main__':
    main()
