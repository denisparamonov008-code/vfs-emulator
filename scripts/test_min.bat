@echo off
REM Проверка минимальной VFS.
py src\emulator.py --vfs vfs-min.csv --script scripts\test_min_commands.txt
