#!/bin/sh
# Проверка VFS с несколькими файлами.
python3 src/emulator.py --vfs vfs-files.csv --script scripts/test_files_commands.txt
