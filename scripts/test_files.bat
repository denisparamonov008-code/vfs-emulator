@echo off
REM Проверка VFS с несколькими файлами.
py src\emulator.py --vfs vfs-files.csv --script scripts\test_files_commands.txt
