#!/usr/bin/env python3
"""
Fix datetime.now(UTC) deprecation warnings across the project
"""

import os
import re
import glob

def fix_file(filepath):
    """Fix datetime.now(UTC) in a single file"""
    print(f"Fixing {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Add UTC import if datetime is imported but UTC is not
        if 'from datetime import' in content and 'UTC' not in content:
            # Find the datetime import line and add UTC
            content = re.sub(
                r'from datetime import ([^,\n]+(?:,\s*[^,\n]+)*)',
                lambda m: f'from datetime import {m.group(1)}, UTC',
                content
            )
        
        # Replace all datetime.now(UTC) with datetime.now(UTC)
        content = re.sub(r'datetime\.utcnow\(\)', 'datetime.now(UTC)', content)
        
        # Only write if changes were made
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✅ Fixed {filepath}")
            return True
        else:
            print(f"  ⚪ No changes needed in {filepath}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error fixing {filepath}: {str(e)}")
        return False

def main():
    """Fix all Python files in the project"""
    print("🔧 FIXING datetime.now(UTC) DEPRECATION WARNINGS")
    print("="*60)
    
    # Find all Python files
    patterns = [
        'app/**/*.py',
        'scripts/*.py',
        '*.py'
    ]
    
    files_to_fix = []
    for pattern in patterns:
        files_to_fix.extend(glob.glob(pattern, recursive=True))
    
    # Remove duplicates and sort
    files_to_fix = sorted(set(files_to_fix))
    
    print(f"Found {len(files_to_fix)} Python files to check")
    
    fixed_count = 0
    for filepath in files_to_fix:
        if fix_file(filepath):
            fixed_count += 1
    
    print(f"\n🎉 COMPLETED: Fixed {fixed_count} files")
    print("All datetime.now(UTC) calls have been replaced with datetime.now(UTC)")

if __name__ == "__main__":
    main() 