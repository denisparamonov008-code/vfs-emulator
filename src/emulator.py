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


def cmd_exit(args):
    """Завершает работу оболочки."""
    if args:
        print("error: использование: exit")
        return
    raise SystemExit


def cmd_help(args):
    """Показывает справку."""
    if args:
        print("error: использование: help")
        return
    show_help()


def cmd_stub(command, args):
    """Заглушка: печатает имя команды и аргументы."""
    print(command, *args)


def cmd_dispatch(command, args):
    """Вызывает обработчик команды."""
    if command == "exit":
        cmd_exit(args)
    elif command == "help":
        cmd_help(args)
    elif command in ("ls", "cd"):
        cmd_stub(command, args)
    else:
        print(f"error: неизвестная команда: {command}")


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
    cmd_dispatch(command, args)


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
