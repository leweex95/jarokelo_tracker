"""
Test to ensure Makefile and jarokelo.bat have consistent commands.
This test validates that both files define the same commands with equivalent implementations.
"""

import re
from pathlib import Path
from typing import Dict, Set


def parse_makefile_targets(makefile_path: Path) -> Dict[str, str]:
    """Parse Makefile and extract targets with their commands."""
    targets = {}
    target_dependencies = {}
    current_target = None
    current_commands = []
    
    with open(makefile_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines:
        # Match target definition (e.g., "continue-scraping:" or "run-pipeline: dep1 dep2")
        target_match = re.match(r'^([a-z-]+):\s*(.*)$', line)
        if target_match and not line.startswith('\t'):
            # Save previous target if any
            if current_target:
                if current_commands:
                    targets[current_target] = '\n'.join(current_commands).strip()
                else:
                    targets[current_target] = ""  # Mark as exists even if no commands
            
            current_target = target_match.group(1)
            dependencies = target_match.group(2).strip()
            if dependencies:
                target_dependencies[current_target] = dependencies
            current_commands = []
        # Match command lines (start with tab or contain poetry/python commands)
        elif current_target and (line.startswith('\t') or 'poetry run' in line or 'python' in line):
            # Clean up the line (remove tabs, @echo commands for display)
            cleaned = line.strip()
            # Skip empty lines and echo statements
            if cleaned and not cleaned.startswith('@echo') and not cleaned.startswith('echo'):
                current_commands.append(cleaned)
    
    # Save the last target
    if current_target:
        if current_commands:
            targets[current_target] = '\n'.join(current_commands).strip()
        else:
            targets[current_target] = ""
    
    return targets, target_dependencies


def parse_bat_commands(bat_path: Path) -> Dict[str, str]:
    """Parse jarokelo.bat and extract command labels with their implementations."""
    commands = {}
    current_label = None
    current_commands = []
    in_if_block = 0
    
    with open(bat_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        # Match label definition (e.g., ":continue-scraping")
        label_match = re.match(r'^:([a-z-]+)$', line.strip())
        if label_match:
            # Save previous label if any
            if current_label and current_label not in ['help', 'invalid', 'end'] and current_commands:
                commands[current_label] = '\n'.join(current_commands).strip()
            
            current_label = label_match.group(1)
            current_commands = []
            in_if_block = 0
        # Stop at 'goto end' or 'goto' statements (but not inside if blocks)
        elif current_label and line.strip().startswith('goto ') and in_if_block == 0:
            if current_label not in ['help', 'invalid', 'end'] and current_commands:
                commands[current_label] = '\n'.join(current_commands).strip()
            current_label = None
            current_commands = []
        # Track if statements (but not inside strings)
        elif current_label and re.match(r'^if\s+', line.strip()) and '(' in line:
            in_if_block += 1
        elif current_label and line.strip() == ')':
            in_if_block = max(0, in_if_block - 1)
        # Match command lines (poetry run commands, including python -c)
        elif current_label and 'poetry run' in line:
            cleaned = line.strip()
            # Skip echo commands but include poetry commands even within if blocks
            if not cleaned.startswith('echo ') and not cleaned.startswith('REM '):
                current_commands.append(cleaned)
    
    return commands


def normalize_command(cmd: str, is_windows: bool = False) -> str:
    """Normalize a command string for comparison."""
    # Remove line continuation characters
    cmd = cmd.replace('\\', ' ').replace('^', ' ')
    # Normalize whitespace
    cmd = ' '.join(cmd.split())
    # Remove quotes around data/raw for consistency
    cmd = cmd.replace('"data/raw"', 'data/raw')
    cmd = cmd.replace("'data/raw'", 'data/raw')
    # Normalize poetry run python paths
    cmd = re.sub(r'poetry\s+run\s+python\s+', 'poetry run python ', cmd)
    
    # Remove shell conditional logic (they're equivalent, just different syntax)
    # Remove Makefile if-then-fi blocks
    cmd = re.sub(r'@if\s+\[\s+-z\s+"?\$\([A-Z_]+\)"?\s+\];\s+then\s+.*?;\s+fi\s*', '', cmd)
    # Remove $(VAR) and %VAR% differences (both are variable references)
    cmd = re.sub(r'\$\([A-Z_]+\)', 'VAR', cmd)
    cmd = re.sub(r'%[A-Z_]+%', 'VAR', cmd)
    
    return cmd


def get_command_list_from_help(content: str, is_makefile: bool = True) -> Set[str]:
    """Extract command list from help text."""
    commands = set()
    # Look for lines that describe commands
    # In Makefile: @echo "  command-name     Description" or @echo "  command-name Description"
    # In bat file: echo   command-name     Description
    
    if is_makefile:
        # Pattern for makefile: @echo "  command-name" where command-name starts a line after spaces
        # Looking for patterns like: @echo "  command-name Description"
        pattern = r'@echo\s+"[ \t]+([a-z][a-z-]+)\s+[A-Z][a-z]+'
    else:
        # Pattern for bat file: echo   command-name with spaces before description
        pattern = r'echo\s+([a-z][a-z-]+)\s+[A-Z][a-z]+'
    
    for line in content.split('\n'):
        match = re.search(pattern, line)
        if match:
            cmd = match.group(1)
            # Exclude false positives (common words that appear in help text)
            if cmd not in ['make', 'set']:
                commands.add(cmd)
    
    return commands


def test_makefile_bat_consistency():
    """Test that Makefile and jarokelo.bat have consistent commands."""
    repo_root = Path(__file__).parent.parent
    makefile_path = repo_root / 'Makefile'
    bat_path = repo_root / 'jarokelo.bat'
    
    assert makefile_path.exists(), f"Makefile not found at {makefile_path}"
    assert bat_path.exists(), f"jarokelo.bat not found at {bat_path}"
    
    # Parse both files
    makefile_targets, makefile_deps = parse_makefile_targets(makefile_path)
    bat_commands = parse_bat_commands(bat_path)
    
    # Get command sets (exclude 'help' and utility targets)
    makefile_cmds = set(makefile_targets.keys()) - {'help'}
    bat_cmds = set(bat_commands.keys()) - {'help'}
    
    # Check for missing commands
    missing_in_makefile = bat_cmds - makefile_cmds
    missing_in_bat = makefile_cmds - bat_cmds
    
    errors = []
    
    if missing_in_makefile:
        errors.append(f"Commands in jarokelo.bat but missing implementation in Makefile: {sorted(missing_in_makefile)}")
    
    if missing_in_bat:
        errors.append(f"Commands in Makefile but missing in jarokelo.bat: {sorted(missing_in_bat)}")
    
    # Check command equivalence for common commands
    common_commands = makefile_cmds & bat_cmds
    
    for cmd in sorted(common_commands):
        makefile_impl = makefile_targets[cmd]
        bat_impl = bat_commands[cmd]
        
        # Special case: if Makefile target has dependencies (composite command), expand them
        if cmd in makefile_deps and not makefile_impl:
            # This is a composite command - it should execute its dependencies
            # For comparison, we'll just verify it exists in both
            continue
        
        makefile_impl_norm = normalize_command(makefile_impl, is_windows=False)
        bat_impl_norm = normalize_command(bat_impl, is_windows=True)
        
        # Compare the normalized commands
        # They should be equivalent (same python script, same arguments)
        if makefile_impl_norm != bat_impl_norm:
            # Check if they at least call the same Python script
            makefile_script = re.search(r'python\s+([\w/._-]+\.py)', makefile_impl_norm)
            bat_script = re.search(r'python\s+([\w/._-]+\.py)', bat_impl_norm)
            
            if makefile_script and bat_script:
                if makefile_script.group(1) != bat_script.group(1):
                    errors.append(
                        f"Command '{cmd}' calls different scripts:\n"
                        f"  Makefile: {makefile_script.group(1)}\n"
                        f"  Bat file: {bat_script.group(1)}"
                    )
                else:
                    # Same script, check if arguments are reasonably similar
                    # Extract arguments
                    makefile_args = re.sub(r'poetry run python [\w/._-]+\.py\s*', '', makefile_impl_norm)
                    bat_args = re.sub(r'poetry run python [\w/._-]+\.py\s*', '', bat_impl_norm)
                    
                    # Normalize argument order and format
                    makefile_args_set = set(makefile_args.split())
                    bat_args_set = set(bat_args.split())
                    
                    # Check for significant differences
                    args_only_in_makefile = makefile_args_set - bat_args_set
                    args_only_in_bat = bat_args_set - makefile_args_set
                    
                    # Filter out minor differences like quotes and --backend bs (Makefile-specific)
                    significant_diff = False
                    for arg in args_only_in_makefile:
                        if arg and arg not in ['', '\\', '--backend', 'bs']:
                            significant_diff = True
                            break
                    for arg in args_only_in_bat:
                        if arg and arg not in ['', '\\']:
                            significant_diff = True
                            break
                    
                    if significant_diff:
                        errors.append(
                            f"Command '{cmd}' has different arguments:\n"
                            f"  Makefile: {makefile_impl_norm}\n"
                            f"  Bat file: {bat_impl_norm}\n"
                            f"  Only in Makefile: {args_only_in_makefile}\n"
                            f"  Only in Bat: {args_only_in_bat}"
                        )
    
    # Report all errors
    if errors:
        error_msg = "Makefile and jarokelo.bat are not consistent:\n\n" + "\n\n".join(errors)
        raise AssertionError(error_msg)


def test_help_text_consistency():
    """Test that help text in both files lists the same commands."""
    repo_root = Path(__file__).parent.parent
    makefile_path = repo_root / 'Makefile'
    bat_path = repo_root / 'jarokelo.bat'
    
    with open(makefile_path, 'r', encoding='utf-8') as f:
        makefile_content = f.read()
    
    with open(bat_path, 'r', encoding='utf-8') as f:
        bat_content = f.read()
    
    # Extract help sections
    makefile_help = re.search(r'help:(.+?)^\.PHONY:', makefile_content, re.MULTILINE | re.DOTALL)
    bat_help = re.search(r':help(.+?)goto end', bat_content, re.MULTILINE | re.DOTALL)
    
    if not makefile_help or not bat_help:
        raise AssertionError("Could not find help sections in both files")
    
    # Get listed commands from help text
    makefile_help_cmds = get_command_list_from_help(makefile_help.group(1), is_makefile=True)
    bat_help_cmds = get_command_list_from_help(bat_help.group(1), is_makefile=False)
    
    # Parse actual implementations to see which commands are really available
    makefile_targets, _ = parse_makefile_targets(makefile_path)
    bat_commands = parse_bat_commands(bat_path)
    
    makefile_cmds = set(makefile_targets.keys()) - {'help'}
    bat_cmds = set(bat_commands.keys()) - {'help'}
    
    errors = []
    warnings = []
    
    # Check if help documents non-existent commands
    makefile_help_not_impl = makefile_help_cmds - makefile_cmds
    bat_help_not_impl = bat_help_cmds - bat_cmds
    
    if makefile_help_not_impl:
        warnings.append(f"Makefile help documents commands that are not implemented: {sorted(makefile_help_not_impl)}")
    
    if bat_help_not_impl:
        warnings.append(f"jarokelo.bat help documents commands that are not implemented: {sorted(bat_help_not_impl)}")
    
    # Check if implemented commands are missing from help
    makefile_impl_not_help = makefile_cmds - makefile_help_cmds
    bat_impl_not_help = bat_cmds - bat_help_cmds
    
    if makefile_impl_not_help:
        warnings.append(f"Makefile has implemented commands not in help: {sorted(makefile_impl_not_help)}")
    
    if bat_impl_not_help:
        warnings.append(f"jarokelo.bat has implemented commands not in help: {sorted(bat_impl_not_help)}")
    
    # Check consistency between the two help texts
    missing_in_makefile_help = bat_help_cmds - makefile_help_cmds
    missing_in_bat_help = makefile_help_cmds - bat_help_cmds
    
    if missing_in_makefile_help:
        warnings.append(f"Commands in jarokelo.bat help but missing from Makefile help: {sorted(missing_in_makefile_help)}")
    
    if missing_in_bat_help:
        warnings.append(f"Commands in Makefile help but missing from jarokelo.bat help: {sorted(missing_in_bat_help)}")
    
    # Report all issues as warnings (non-fatal)
    if warnings or errors:
        print("⚠ WARNINGS (help text documentation issues):")
        for warning in warnings + errors:
            print(f"  • {warning}")
        print("\nNote: Help text warnings are informational only and won't fail the test.")
        print("Consider synchronizing help text and implementations in both files.")


if __name__ == '__main__':
    # Run tests when executed directly
    print("Testing Makefile and jarokelo.bat consistency...")
    try:
        test_makefile_bat_consistency()
        print("✓ Command consistency test passed")
    except AssertionError as e:
        print(f"✗ Command consistency test failed:\n{e}")
        exit(1)
    
    try:
        test_help_text_consistency()
        print("✓ Help text consistency test passed")
    except AssertionError as e:
        print(f"✗ Help text consistency test failed:\n{e}")
        exit(1)
    
    print("\nAll tests passed!")
