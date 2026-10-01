@echo off
REM Проверка VFS с несколькими уровнями.
py src\emulator.py --vfs vfs-deep.csv --script scripts\test_deep_commands.txt
