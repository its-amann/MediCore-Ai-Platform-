#!/usr/bin/env python3
"""
Migration Script to Unified Logging System

This script helps migrate existing logging code to the unified logging system.
It can run in dry-run mode to preview changes or apply them directly.

Usage:
    python migrate_to_unified_logging.py --dry-run  # Preview changes
    python migrate_to_unified_logging.py            # Apply changes
"""

import os
import re
import argparse
from pathlib import Path
from typing import List, Tuple, Dict
import difflib
from collections import defaultdict


class LoggingMigrator:
    """Migrate existing logging to unified system"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.stats = defaultdict(int)
        self.files_to_update = []
        
        # Patterns to find and replace
        self.patterns = [
            # Standard logging imports
            (r'import logging\b', 'from app.core.unified_logging import get_logger'),
            (r'from logging import .*', 'from app.core.unified_logging import get_logger'),
            
            # Logger creation
            (r'logger = logging\.getLogger\((.*?)\)', r'logger = get_logger(\1)'),
            (r'self\.logger = logging\.getLogger\((.*?)\)', r'self.logger = get_logger(\1)'),
            
            # EnhancedLogger imports and usage
            (r'from app\.core\.enhanced_logging import EnhancedLogger', 
             'from app.core.unified_logging import get_logger'),
            (r'EnhancedLogger\((.*?)\)', r'get_logger(\1)'),
            
            # Simple logging setup
            (r'logging\.basicConfig\(.*?\)', '# Logging configured by unified system'),
            
            # Direct logging calls
            (r'\blogging\.info\((.*?)\)', r'get_logger(__name__).info(\1)'),
            (r'\blogging\.debug\((.*?)\)', r'get_logger(__name__).debug(\1)'),
            (r'\blogging\.warning\((.*?)\)', r'get_logger(__name__).warning(\1)'),
            (r'\blogging\.error\((.*?)\)', r'get_logger(__name__).error(\1)'),
            (r'\blogging\.critical\((.*?)\)', r'get_logger(__name__).critical(\1)'),
            
            # Print statements (convert to logging)
            (r'print\(f?"([^"]+)"\)', r'get_logger(__name__).info("\1")'),
            (r"print\(f?'([^']+)'\)", r'get_logger(__name__).info("\1")'),
        ]
        
        # Special handlers for complex cases
        self.special_handlers = {
            'middleware': self._handle_middleware,
            'mcp_server': self._handle_mcp_server,
            'main.py': self._handle_main_file
        }
    
    def migrate(self, root_dir: str = 'app'):
        """Run migration on all Python files"""
        print(f"Starting migration in {'DRY RUN' if self.dry_run else 'LIVE'} mode...")
        
        # Find all Python files
        for py_file in Path(root_dir).rglob('*.py'):
            # Skip migration files and unified logging itself
            if any(skip in str(py_file) for skip in [
                'migrate_to_unified_logging.py',
                'unified_logging.py',
                'unified_middleware.py',
                'logging_config.py',
                '__pycache__'
            ]):
                continue
            
            self._process_file(py_file)
        
        # Print summary
        self._print_summary()
    
    def _process_file(self, file_path: Path):
        """Process a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return
        
        modified_content = original_content
        changes_made = False
        
        # Apply patterns
        for pattern, replacement in self.patterns:
            new_content = re.sub(pattern, replacement, modified_content, flags=re.MULTILINE)
            if new_content != modified_content:
                changes_made = True
                self.stats['patterns_applied'] += 1
            modified_content = new_content
        
        # Apply special handlers
        for handler_key, handler_func in self.special_handlers.items():
            if handler_key in str(file_path):
                modified_content, handler_changes = handler_func(modified_content)
                if handler_changes:
                    changes_made = True
                    self.stats['special_handlers'] += 1
        
        # Add import if needed and not already present
        if changes_made and 'get_logger' in modified_content and 'from app.core.unified_logging import' not in modified_content:
            # Add import at the top after other imports
            lines = modified_content.split('\n')
            import_added = False
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    # Found imports section
                    continue
                elif not line.strip() and i > 0:
                    # Empty line after imports
                    lines.insert(i, 'from app.core.unified_logging import get_logger')
                    import_added = True
                    break
            
            if import_added:
                modified_content = '\n'.join(lines)
                self.stats['imports_added'] += 1
        
        # Save or display changes
        if changes_made:
            self.files_to_update.append(file_path)
            self.stats['files_modified'] += 1
            
            if self.dry_run:
                self._show_diff(file_path, original_content, modified_content)
            else:
                self._save_file(file_path, modified_content)
    
    def _handle_middleware(self, content: str) -> Tuple[str, bool]:
        """Special handling for middleware files"""
        changes = False
        
        # Update LoggingMiddleware references
        if 'LoggingMiddleware' in content:
            content = content.replace(
                'from app.middleware.logging import LoggingMiddleware',
                'from app.api.unified_middleware import UnifiedLoggingMiddleware'
            )
            content = content.replace(
                'app.add_middleware(LoggingMiddleware)',
                'app.add_middleware(UnifiedLoggingMiddleware)'
            )
            changes = True
        
        return content, changes
    
    def _handle_mcp_server(self, content: str) -> Tuple[str, bool]:
        """Special handling for MCP server files"""
        changes = False
        
        # Update MCP-specific logging
        if 'setup_logging' in content:
            content = re.sub(
                r'def setup_logging\(.*?\):.*?(?=\ndef|\nclass|\Z)',
                '''def setup_logging(log_level: str = "INFO"):
    """Setup logging using unified system"""
    from app.core.unified_logging import get_logger
    logger = get_logger('medical_mcp')
    return logger
''',
                content,
                flags=re.DOTALL
            )
            changes = True
        
        return content, changes
    
    def _handle_main_file(self, content: str) -> Tuple[str, bool]:
        """Special handling for main.py files"""
        changes = False
        
        # Add unified logging initialization
        if 'app = FastAPI' in content and 'initialize_logging' not in content:
            content = re.sub(
                r'(app = FastAPI\(.*?\))',
                r'''# Initialize unified logging
from app.core.logging_config import initialize_logging
from app.api.unified_middleware import setup_unified_middleware

initialize_logging()

\1

# Setup unified middleware
setup_unified_middleware(app)''',
                content
            )
            changes = True
        
        return content, changes
    
    def _show_diff(self, file_path: Path, original: str, modified: str):
        """Show diff between original and modified content"""
        print(f"\n{'='*60}")
        print(f"Changes for: {file_path}")
        print('='*60)
        
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile=f'{file_path} (original)',
            tofile=f'{file_path} (modified)',
            n=3
        )
        
        for line in diff:
            if line.startswith('+'):
                print(f"\033[92m{line}\033[0m", end='')  # Green
            elif line.startswith('-'):
                print(f"\033[91m{line}\033[0m", end='')  # Red
            else:
                print(line, end='')
    
    def _save_file(self, file_path: Path, content: str):
        """Save modified content to file"""
        try:
            # Create backup
            backup_path = file_path.with_suffix('.py.bak')
            with open(file_path, 'r', encoding='utf-8') as f:
                backup_content = f.read()
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(backup_content)
            
            # Write new content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"[OK] Updated: {file_path}")
            self.stats['files_saved'] += 1
        except Exception as e:
            print(f"[ERROR] Error saving {file_path}: {e}")
            self.stats['save_errors'] += 1
    
    def _print_summary(self):
        """Print migration summary"""
        print(f"\n{'='*60}")
        print("Migration Summary")
        print('='*60)
        print(f"Files analyzed: {self.stats['files_modified'] + self.stats['files_skipped']}")
        print(f"Files to update: {len(self.files_to_update)}")
        print(f"Patterns applied: {self.stats['patterns_applied']}")
        print(f"Special handlers: {self.stats['special_handlers']}")
        print(f"Imports added: {self.stats['imports_added']}")
        
        if not self.dry_run:
            print(f"Files saved: {self.stats['files_saved']}")
            print(f"Save errors: {self.stats['save_errors']}")
        
        if self.files_to_update:
            print("\nFiles to update:")
            for file_path in sorted(self.files_to_update):
                print(f"  - {file_path}")
        
        if self.dry_run:
            print("\nWARNING: This was a DRY RUN. No files were modified.")
            print("Run without --dry-run to apply changes.")


def create_migration_checklist():
    """Create a checklist for manual migration steps"""
    checklist = """
# Unified Logging Migration Checklist

## Automated Steps (handled by migration script)
- [x] Update import statements
- [x] Replace logger creation
- [x] Convert print statements to logging
- [x] Update middleware references
- [x] Add unified logging initialization

## Manual Steps Required

### 1. Environment Variables
Add to your .env file:
```
LOG_LEVEL=INFO
LOG_DIR=./logs
LOG_JSON=false  # Set to true for production
MASK_PII=true   # For HIPAA compliance
HIPAA_COMPLIANT=true
SLOW_REQUEST_THRESHOLD_MS=1000
PERFORMANCE_TRACKING=true

# Service-specific levels
MCP_LOG_LEVEL=INFO
GROQ_LOG_LEVEL=INFO
DB_LOG_LEVEL=INFO
API_LOG_LEVEL=INFO
SECURITY_LOG_LEVEL=INFO
PERF_LOG_LEVEL=INFO
```

### 2. Update Requirements
Add to requirements.txt:
```
psutil>=5.9.0  # For memory monitoring
```

### 3. Remove Old Log Files
```bash
rm -rf logs/*.log
rm -rf logs/archive/
```

### 4. Update Deployment Scripts
- Update log rotation scripts to use new log files
- Update monitoring to parse JSON logs
- Update backup scripts for new log structure

### 5. Test Specialized Logging
Test these features work correctly:
- [ ] Security event logging
- [ ] Audit trail creation
- [ ] Performance metrics
- [ ] Medical operation logging
- [ ] AI model interaction tracking

### 6. Verify Middleware Stack
Ensure middleware is loaded in correct order:
1. CORS
2. Security
3. MedicalOperation
4. AIModel
5. PerformanceMonitoring
6. UnifiedLogging

### 7. Update Documentation
- [ ] Update README with new logging info
- [ ] Document environment variables
- [ ] Add logging examples to developer guide

### 8. Production Considerations
- [ ] Set LOG_JSON=true for structured logs
- [ ] Configure log aggregation service
- [ ] Set up alerts for ERROR/CRITICAL logs
- [ ] Verify HIPAA compliance settings
- [ ] Test log rotation and cleanup

## Rollback Plan
If issues occur:
1. Restore .bak files created by migration
2. Revert environment variables
3. Restart services

## Verification Commands
```bash
# Check logs are being created
ls -la logs/

# Tail main log
tail -f logs/medical_ai.log

# Check for errors
grep ERROR logs/medical_ai.log

# Verify JSON format (if enabled)
cat logs/medical_ai.log | jq .
```
"""
    
    with open('MIGRATION_CHECKLIST.md', 'w') as f:
        f.write(checklist)
    
    print("Created MIGRATION_CHECKLIST.md")


def main():
    parser = argparse.ArgumentParser(description='Migrate to unified logging system')
    parser.add_argument('--dry-run', action='store_true', 
                      help='Preview changes without modifying files')
    parser.add_argument('--root-dir', default='app',
                      help='Root directory to search for Python files')
    parser.add_argument('--create-checklist', action='store_true',
                      help='Create migration checklist')
    
    args = parser.parse_args()
    
    if args.create_checklist:
        create_migration_checklist()
        return
    
    migrator = LoggingMigrator(dry_run=args.dry_run)
    migrator.migrate(args.root_dir)


if __name__ == '__main__':
    main()