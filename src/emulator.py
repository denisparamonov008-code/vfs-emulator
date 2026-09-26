"""Консольный эмулятор UNIX-оболочки для этапов 1-3."""

import argparse
import base64
import csv
import os
import shlex
from dataclasses import dataclass, field
from typing import Callable, Dict, List


class CommandError(Exception):
    """Ошибка выполнения команды."""


@dataclass
class VfsEntry:
    """Элемент виртуальной файловой системы."""

    path: str
    kind: str
    content: str = ""
    encoding: str = "plain"


@dataclass
class VFS:
    """Виртуальная файловая система, полностью загруженная в память."""

    entries: Dict[str, VfsEntry] = field(default_factory=dict)

    @classmethod
    def from_csv(cls, path: str) -> "VFS":
        """Загружает VFS из CSV-файла."""
        result = cls()
        try:
            with open(path, "r", encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                required = {"type", "path", "content", "encoding"}
                if not reader.fieldnames or not required.issubset(reader.fieldnames):
                    raise ValueError("CSV должен содержать type,path,content,encoding")
                for row in reader:
                    item = cls._make_entry(row)
                    result.entries[item.path] = item
        except (OSError, UnicodeError, csv.Error) as exc:
            raise RuntimeError(f"не удалось прочитать VFS: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError(f"ошибка VFS: {exc}") from exc
        result._add_parent_dirs()
        result.entries.setdefault("/", VfsEntry("/", "dir"))
        return result

    @staticmethod
    def _make_entry(row: Dict[str, str]) -> VfsEntry:
        """Создаёт элемент VFS из строки CSV."""
        kind = (row.get("type") or "").strip().lower()
        path = VFS.normalize(row.get("path") or "/")
        content = row.get("content") or ""
        encoding = (row.get("encoding") or "plain").strip().lower()
        if kind not in {"file", "dir"}:
            raise ValueError(f"неизвестный тип {kind} для {path}")
        if encoding == "base64" and kind == "file":
            try:
                content = base64.b64decode(content.encode()).decode("utf-8")
            except (ValueError, UnicodeError) as exc:
                raise ValueError(f"ошибка base64 для {path}") from exc
        return VfsEntry(path, kind, content, encoding)

    def _add_parent_dirs(self) -> None:
        """Добавляет отсутствующие родительские каталоги в память."""
        paths = list(self.entries)
        for path in paths:
            parent = self.parent(path)
            while parent and parent not in self.entries:
                self.entries[parent] = VfsEntry(parent, "dir")
                parent = self.parent(parent)

    @staticmethod
    def normalize(path: str) -> str:
        """Приводит путь к единому абсолютному виду."""
        if not path:
            return "/"
        parts = []
        for part in path.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(part)
        return "/" + "/".join(parts)

    @staticmethod
    def parent(path: str) -> str:
        """Возвращает родительский каталог."""
        path = VFS.normalize(path)
        if path == "/":
            return ""
        value = path.rsplit("/", 1)[0]
        return value or "/"

    def resolve(self, path: str, cwd: str) -> str:
        """Преобразует относительный путь в абсолютный виртуальный путь."""
        if path.startswith("/"):
            return self.normalize(path)
        return self.normalize(f"{cwd}/{path}")

    def list_dir(self, path: str) -> List[str]:
        """Возвращает имена элементов указанного каталога."""
        path = self.normalize(path)
        entry = self.entries.get(path)
        if entry is None or entry.kind != "dir":
            raise CommandError(f"нет такого каталога: {path}")
        prefix = "/" if path == "/" else path + "/"
        names = []
        for item_path in self.entries:
            if not item_path.startswith(prefix) or item_path == path:
                continue
            rest = item_path[len(prefix):]
            if "/" not in rest:
                names.append(rest)
        return sorted(set(names))


@dataclass
class State:
    """Состояние интерактивной сессии."""

    cwd: str = "/"
    history: List[str] = field(default_factory=list)


@dataclass
class Config:
    """Параметры запуска эмулятора."""

    vfs_path: str
    script_path: str


Command = Callable[[List[str], State, Config, VFS], str]


def cmd_ls(args: List[str], state: State, config: Config, vfs: VFS) -> str:
    """Выводит содержимое виртуального каталога."""
    if len(args) > 1:
        raise CommandError("использование: ls [путь]")
    path = vfs.resolve(args[0], state.cwd) if args else state.cwd
    return "  ".join(vfs.list_dir(path))


def cmd_cd(args: List[str], state: State, config: Config, vfs: VFS) -> str:
    """Изменяет виртуальный текущий каталог."""
    if len(args) > 1:
        raise CommandError("использование: cd [каталог]")
    path = vfs.resolve(args[0], state.cwd) if args else "/"
    entry = vfs.entries.get(path)
    if entry is None or entry.kind != "dir":
        raise CommandError(f"нет такого каталога: {path}")
    state.cwd = path
    return ""


def cmd_help(args: List[str], state: State, config: Config, vfs: VFS) -> str:
    """Показывает список поддерживаемых команд."""
    if args:
        raise CommandError("использование: help")
    lines = [
        "ls - список файлов",
        "cd - сменить каталог",
        "help - справка",
        "conf-dump - параметры",
        "exit - выход",
    ]
    return "\n".join(lines)


def cmd_conf_dump(args: List[str], state: State, config: Config, vfs: VFS) -> str:
    """Выводит параметры запуска в формате ключ=значение."""
    if args:
        raise CommandError("использование: conf-dump")
    lines = [
        f"vfs_path={config.vfs_path}",
        f"script_path={config.script_path}",
    ]
    return "\n".join(lines)


COMMANDS: Dict[str, Command] = {
    "ls": cmd_ls,
    "cd": cmd_cd,
    "help": cmd_help,
    "conf-dump": cmd_conf_dump,
}


def execute(line: str, state: State, config: Config, vfs: VFS) -> str:
    """Разбирает и выполняет одну команду."""
    try:
        parts = shlex.split(line)
    except ValueError as exc:
        raise CommandError("ошибка разбора команды") from exc
    if not parts:
        return ""
    command = parts[0]
    args = [os.path.expandvars(item) for item in parts[1:]]
    if command == "exit":
        if args:
            raise CommandError("использование: exit")
        raise EOFError
    if command not in COMMANDS:
        raise CommandError(f"неизвестная команда: {command}")
    return COMMANDS[command](args, state, config, vfs)


def print_motd(vfs: VFS) -> None:
    """Выводит содержимое /motd, если файл существует."""
    item = vfs.entries.get("/motd")
    if item and item.kind == "file":
        print(item.content)


def run_script(path: str, state: State, config: Config, vfs: VFS) -> bool:
    """Выполняет стартовый скрипт построчно."""
    if not path:
        return False
    try:
        with open(path, "r", encoding="utf-8") as file:
            for number, raw in enumerate(file, 1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                print(f"{prompt(state)}{line}")
                try:
                    output = execute(line, state, config, vfs)
                except EOFError:
                    return True
                except CommandError as exc:
                    print(f"error: строка {number}: {exc}")
                    continue
                if output:
                    print(output)
    except OSError as exc:
        raise RuntimeError(
            f"не удалось выполнить стартовый скрипт: {exc}"
        ) from exc
    return False


def prompt(state: State) -> str:
    """Формирует приглашение командной строки."""
    return f"vfs:{state.cwd}$ "


def parse_args() -> Config:
    """Разбирает параметры командной строки."""
    parser = argparse.ArgumentParser(description="Эмулятор UNIX-оболочки")
    parser.add_argument("--vfs", required=True, help="путь к VFS")
    parser.add_argument("--script", default="", help="путь к стартовому скрипту")
    args = parser.parse_args()
    script = args.script or "<none>"
    return Config(vfs_path=args.vfs, script_path=script)


def main() -> None:
    """Запускает эмулятор и интерактивный режим."""
    config = parse_args()
    try:
        vfs = VFS.from_csv(config.vfs_path)
    except RuntimeError as exc:
        print(f"error: {exc}")
        return
    state = State()
    print(f"vfs_path={config.vfs_path}")
    print(f"script_path={config.script_path}")
    print_motd(vfs)
    script = "" if config.script_path == "<none>" else config.script_path
    try:
        stopped = run_script(script, state, config, vfs)
    except RuntimeError as exc:
        print(f"error: {exc}")
        return
    if stopped:
        return
    while True:
        try:
            line = input(prompt(state))
            if line.strip():
                state.history.append(line)
            output = execute(line, state, config, vfs)
            if output:
                print(output)
        except EOFError:
            print()
            break
        except CommandError as exc:
            print(f"error: {exc}")


if __name__ == "__main__":
    main()
