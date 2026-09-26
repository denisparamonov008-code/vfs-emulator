#!/bin/sh
# Проверка минимальной VFS.
python3 src/emulator.py --vfs vfs-min.csv --script scripts/test_min_commands.txt
