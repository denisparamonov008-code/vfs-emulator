"""Этап 2: настраиваемый эмулятор оболочки."""

import argparse
import os
import shlex
from dataclasses import dataclass


VFS_NAME = "vfs"


@dataclass
class Config:
    """Параметры запуска эмулятора."""

    vfs_path: str
    script_path: str


def show_help():
    """Показывает список доступных команд."""
    print("Доступные команды:")
    print("ls - список файлов")
    print("cd - смена каталога")
    print("help - справка")
    print("conf-dump - параметры")
    print("exit - выход")


def cmd_conf_dump(args, config):
    """Печатает параметры как ключ=значение."""
    if args:
        print("error: использование: conf-dump")
        return
    print(f"vfs_path={config.vfs_path}")
    print(f"script_path={config.script_path}")


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


def cmd_dispatch(command, args, config):
    """Вызывает обработчик команды."""
    if command == "exit":
        cmd_exit(args)
    elif command == "help":
        cmd_help(args)
    elif command == "conf-dump":
        cmd_conf_dump(args, config)
    elif command in ("ls", "cd"):
        cmd_stub(command, args)
    else:
        print(f"error: неизвестная команда: {command}")


def execute(line, config):
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
    cmd_dispatch(command, args, config)


def prompt():
    """Формирует приглашение к вводу."""
    return f"{VFS_NAME}:$ "


def run_script(path, config):
    """Выполняет стартовый скрипт построчно."""
    if not path:
        return False
    try:
        with open(path, "r", encoding="utf-8") as file:
            for number, raw in enumerate(file, 1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                print(f"{prompt()}{line}")
                try:
                    execute(line, config)
                except SystemExit:
                    return True
                except Exception as exc:
                    print(f"error: строка {number}: {exc}")
                    continue
    except OSError as exc:
        print(f"error: стартовый скрипт: {exc}")
        return True
    return False


def parse_args():
    """Разбирает параметры командной строки."""
    parser = argparse.ArgumentParser(
        description="Эмулятор оболочки"
    )
    parser.add_argument("--vfs", required=True, help="путь к VFS")
    parser.add_argument(
        "--script", default="", help="стартовый скрипт"
    )
    args = parser.parse_args()
    script = args.script or "<none>"
    return Config(vfs_path=args.vfs, script_path=script)


def main():
    """Запускает эмулятор."""
    config = parse_args()
    print(f"vfs_path={config.vfs_path}")
    print(f"script_path={config.script_path}")
    script = ""
    if config.script_path != "<none>":
        script = config.script_path
    stopped = run_script(script, config)
    if stopped:
        return
    while True:
        try:
            line = input(prompt())
            execute(line, config)
        except EOFError:
            print()
            break


if __name__ == "__main__":
    main()
