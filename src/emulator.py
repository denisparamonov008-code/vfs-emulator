"""Этап 1: простой эмулятор UNIX-оболочки."""

import os
import shlex


VFS_NAME = "vfs"


def show_help():
    """Показывает список доступных команд."""
    print("Доступные команды:")
    print("ls - список файлов")
    print("cd - смена каталога")
    print("help - справка")
    print("exit - выход")


def execute(line):
    """Разбирает и выполняет одну команду."""
    try:
        parts = shlex.split(line)
    except ValueError:
        print("error: ошибка разбора команды")
        return

    if not parts:
        return

    command = parts[0]
    args = [os.path.expandvars(arg) for arg in parts[1:]]

    if command == "exit":
        if args:
            print("error: использование: exit")
            return
        raise SystemExit

    if command == "help":
        if args:
            print("error: использование: help")
            return
        show_help()
        return

    if command == "ls":
        print("ls", *args)
        return

    if command == "cd":
        print("cd", *args)
        return

    print(f"error: неизвестная команда: {command}")


def main():
    """Запускает командную оболочку."""
    while True:
        try:
            line = input(f"{VFS_NAME}:$ ")
            execute(line)
        except EOFError:
            print()
            break


if __name__ == "__main__":
    main()
