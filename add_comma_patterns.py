#!/usr/bin/env python3
"""Add comma-terminated telemetry patterns to bot.py"""

import re

with open('/root/telegram-acpx-devbot/bot.py', 'r') as f:
    content = f.read()

# Find the usage tracking section and add comma-terminated patterns
# Look for the line that says "# Usage tracking"
pattern = r"(# Usage tracking\n)(            # Usage tracking.*?\n)"

# New comma-terminated patterns to add
new_patterns = """            'used: null,',  # Match with comma
            'size: 200000,',  # Match with comma
            'size: 200000,',  # Match with comma
            'cost: [Object],',  # Match with comma
            'cost: [Object],',  # Match with comma
"""

# Insert new patterns after "# Usage tracking"
match = re.search(pattern, content)
if match:
    # Find where to insert (after the existing usage tracking patterns)
    insert_pos = match.end()
    
    # Find the end of the usage tracking section (before "Error codes")
    # We need to insert new patterns before "Error codes"
    error_codes_pos = content.find("\n            # Error codes")
    
    if error_codes_pos > insert_pos:
        # Insert new patterns at error_codes_pos
        content = content[:error_codes_pos] + new_patterns + "\n" + content[error_codes_pos:]
        
        with open('/root/telegram-acpx-devbot/bot.py', 'w') as f:
            f.write(content)
        print("✅ Added comma-terminated telemetry patterns")
    else:
        print("❌ Could not find '# Error codes' section")
else:
    print("❌ Could not find '# Usage tracking' section")
