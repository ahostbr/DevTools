#!/usr/bin/env python3
"""
Small scanner that detects probable ad-hoc tag writes to gameplay tag containers
by searching for `.AddTag(` and `.RemoveTag(` usage outside the SOTS_TagManager plugin.

This is a heuristic and will generate false positives (e.g., AddTag on arrays of FNames),
so manual review is recommended when it reports results.
"""

import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PLUGINS = os.path.join(ROOT, 'Plugins')

if not os.path.isdir(PLUGINS):
    print('Plugins directory not found: ', PLUGINS)
    sys.exit(1)

pattern = re.compile(r'\b(\.AddTag|\.RemoveTag)\s*\(')

whitelist_plugins = {
    'SOTS_TagManager',
    # The rest of the project tags that are ok to mutate (add more if required)
}

matches = []
for dirpath, dirnames, filenames in os.walk(PLUGINS):
    # Determine plugin name by the path imediately under Plugins
    rel = os.path.relpath(dirpath, PLUGINS)
    parts = rel.split(os.sep)
    if parts[0] in whitelist_plugins:
        continue

    for fname in filenames:
        if not fname.endswith(('.cpp', '.cc', '.h', '.hpp')):
            continue
        fpath = os.path.join(dirpath, fname)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                for i, line in enumerate(fh, start=1):
                    if pattern.search(line):
                        matches.append((fpath, i, line.strip()))
        except Exception as e:
            print('Failed to read', fpath, e)

if not matches:
    print('No suspicious AddTag/RemoveTag usage found outside of SOTS_TagManager.')
    sys.exit(0)

print('\nSuspicious AddTag/RemoveTag usage (heuristic):\n')
for fpath, line_no, line in matches:
    print('{}:{} -> {}'.format(os.path.relpath(fpath, ROOT), line_no, line))

# Optional: exit with non-zero code to fail CI if configured
sys.exit(0)
