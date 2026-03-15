#!/usr/bin/env python3
"""Add comma-terminated telemetry patterns to bot.py at line 260"""

# Read file
with open('/root/telegram-acpx-devbot/bot.py', 'r') as f:
    lines = f.readlines()

# Line 260 is 0-indexed, so we insert before line 260 (0-indexed)
insert_after_line = 259  # Line 260 in 1-indexed

# Patterns to insert (must match exact spacing)
new_patterns = [
    '            \'"used": { "_errors",\n',
    '            "used: null,\n',
    '            "size: 200000,\n',
    '            "size: 200000,\n',
    '            \'"cost": { "_errors",\n',
    '            "cost: [Object],\n',
    '            "cost: [Object],\n'
]

# Insert patterns after line 259
lines = lines[:insert_after_line + 1] + new_patterns + lines[insert_after_line + 1:]

# Write back
with open('/root/telegram-acpx-devbot/bot.py', 'w') as f:
    f.writelines(lines)

print("✅ Added comma-terminated telemetry patterns")
print(f"Inserted {len(new_patterns)} new lines after line {insert_after_line + 1}")
