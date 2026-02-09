"""Test backend structure without external dependencies."""

import os
import ast
from pathlib import Path


def test_file_syntax(file_path):
    """Test if Python file has valid syntax."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


def main():
    """Test all Python files for syntax errors."""
    python_files = []
    
    # Find all Python files
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"Testing {len(python_files)} Python files for syntax errors...")
    
    errors = []
    for file_path in python_files:
        valid, error = test_file_syntax(file_path)
        if valid:
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}: {error}")
            errors.append((file_path, error))
    
    print("\n" + "=" * 50)
    if errors:
        print(f"❌ Found {len(errors)} syntax errors")
        for file_path, error in errors:
            print(f"  {file_path}: {error}")
        return 1
    else:
        print("✅ All Python files have valid syntax")
        print("\nBackend foundation structure is ready!")
        return 0


if __name__ == "__main__":
    exit(main())