#!/bin/sh
# Этап 2: проверка параметров и стартового скрипта.
python3 src/emulator.py --vfs vfs.csv --script scripts/test_config_commands.txt
