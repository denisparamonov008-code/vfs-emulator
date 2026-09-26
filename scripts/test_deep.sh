#!/bin/sh
# Проверка VFS с несколькими уровнями.
python3 src/emulator.py --vfs vfs-deep.csv --script scripts/test_deep_commands.txt
