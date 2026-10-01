"""Эмулятор UNIX-оболочки, этапы 1-4."""

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
    """Виртуальная файловая система."""

    entries: Dict[str, VfsEntry] = field(default_factory=dict)

    @classmethod
    def from_csv(cls, path: str) -> "VFS":
        """Загружает VFS из CSV-файла."""
        result = cls()
        try:
            with open(path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                required = {"type", "path", "content", "encoding"}
                names = reader.fieldnames or []
                if not required.issubset(names):
                    raise ValueError(
                        "CSV: нужны type,path,content,encoding"
                    )
                for row in reader:
                    item = cls._make_entry(row)
                    result.entries[item.path] = item
        except (OSError, UnicodeError, csv.Error) as exc:
            raise RuntimeError(
                f"не удалось прочитать VFS: {exc}"
            ) from exc
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
            raise ValueError(f"тип {kind} для {path}")
        if encoding == "base64" and kind == "file":
            try:
                raw = base64.b64decode(content.encode())
                content = raw.decode("utf-8")
            except (ValueError, UnicodeError) as exc:
                raise ValueError(
                    f"ошибка base64 для {path}"
                ) from exc
        return VfsEntry(path, kind, content, encoding)

    def _add_parent_dirs(self) -> None:
        """Добавляет недостающие каталоги."""
        paths = list(self.entries)
        for path in paths:
            parent = self.parent(path)
            while parent and parent not in self.entries:
                self.entries[parent] = VfsEntry(parent, "dir")
                parent = self.parent(parent)

    @staticmethod
    def normalize(path: str) -> str:
        """Приводит путь к абсолютному виду."""
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
        """Делает путь абсолютным виртуальным."""
        if path.startswith("/"):
            return self.normalize(path)
        return self.normalize(f"{cwd}/{path}")

    def list_dir(self, path: str) -> List[str]:
        """Имена элементов каталога."""
        path = self.normalize(path)
        entry = self.entries.get(path)
        if entry is None or entry.kind != "dir":
            raise CommandError(f"нет такого каталога: {path}")
        prefix = "/" if path == "/" else path + "/"
        names = []
        for item_path in self.entries:
            if not item_path.startswith(prefix):
                continue
            if item_path == path:
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


def cmd_ls(args, state, config, vfs) -> str:
    """Содержимое виртуального каталога."""
    if len(args) > 1:
        raise CommandError("использование: ls [путь]")
    if args:
        path = vfs.resolve(args[0], state.cwd)
    else:
        path = state.cwd
    return "  ".join(vfs.list_dir(path))


def cmd_cd(args, state, config, vfs) -> str:
    """Изменяет виртуальный текущий каталог."""
    if len(args) > 1:
        raise CommandError("использование: cd [каталог]")
    if args:
        path = vfs.resolve(args[0], state.cwd)
    else:
        path = "/"
    entry = vfs.entries.get(path)
    if entry is None or entry.kind != "dir":
        raise CommandError(f"нет такого каталога: {path}")
    state.cwd = path
    return ""


def cmd_help(args, state, config, vfs) -> str:
    """Список поддерживаемых команд."""
    if args:
        raise CommandError("использование: help")
    lines = [
        "ls - список файлов",
        "cd - сменить каталог",
        "help - справка",
        "conf-dump - параметры",
        "history - история команд",
        "tail - конец файла",
        "exit - выход",
    ]
    return "\n".join(lines)


def cmd_conf_dump(args, state, config, vfs) -> str:
    """Печатает параметры как ключ=значение."""
    if args:
        raise CommandError("использование: conf-dump")
    lines = [
        f"vfs_path={config.vfs_path}",
        f"script_path={config.script_path}",
    ]
    return "\n".join(lines)


def cmd_history(args, state, config, vfs) -> str:
    """Показывает историю команд сессии."""
    if args:
        raise CommandError("использование: history")
    lines = []
    for num, line in enumerate(state.history, 1):
        lines.append(f"{num}  {line}")
    return "\n".join(lines)


def cmd_tail(args, state, config, vfs) -> str:
    """Выводит конец файла VFS."""
    count = 10
    rest = list(args)
    if len(rest) >= 2 and rest[0] == "-n":
        try:
            count = int(rest[1])
        except ValueError:
            raise CommandError("tail: нужно число строк")
        if count < 0:
            raise CommandError("tail: нужно число строк")
        rest = rest[2:]
    if len(rest) != 1:
        raise CommandError("использование: tail [-n N] файл")
    path = vfs.resolve(rest[0], state.cwd)
    entry = vfs.entries.get(path)
    if entry is None or entry.kind != "file":
        raise CommandError(f"нет такого файла: {path}")
    rows = entry.content.splitlines()
    return "\n".join(rows[max(0, len(rows) - count):])


COMMANDS: Dict[str, Command] = {
    "ls": cmd_ls,
    "cd": cmd_cd,
    "help": cmd_help,
    "conf-dump": cmd_conf_dump,
    "history": cmd_history,
    "tail": cmd_tail,
}


def execute(line: str, state: State, config: Config, vfs: VFS) -> str:
    """Разбирает и выполняет одну команду."""
    try:
        parts = shlex.split(line)
    except ValueError as exc:
        raise CommandError("ошибка разбора") from exc
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
    """Выводит /motd, если файл существует."""
    item = vfs.entries.get("/motd")
    if item and item.kind == "file":
        print(item.content)


def run_script(path, state, config, vfs) -> bool:
    """Выполняет стартовый скрипт построчно."""
    if not path:
        return False
    try:
        with open(path, "r", encoding="utf-8") as file:
            for number, raw in enumerate(file, 1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                state.history.append(line)
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
            f"стартовый скрипт: {exc}"
        ) from exc
    return False


def prompt(state: State) -> str:
    """Приглашение командной строки."""
    return f"vfs:{state.cwd}$ "


def parse_args() -> Config:
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


def main() -> None:
    """Запускает эмулятор."""
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
    if config.script_path == "<none>":
        script = ""
    else:
        script = config.script_path
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
