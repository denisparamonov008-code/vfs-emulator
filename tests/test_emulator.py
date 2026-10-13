"""Тесты эмулятора: VFS, команды этапов 1-5."""

import os
import tempfile
import unittest

from src.emulator import (
    CommandError,
    Config,
    State,
    VFS,
    execute,
)

CSV_ROWS = [
    "type,path,content,encoding",
    "dir,/, ,plain",
    "dir,/home,,plain",
    "dir,/home/user,,plain",
    "dir,/home/user/docs,,plain",
    "file,/motd,Hello,plain",
    "file,/home/user/data.txt,SGVsbG8=,base64",
    "file,/home/user/log.txt,\"a\nb\nc\nd\",plain",
]


def write_csv(rows):
    """Пишет временный CSV и возвращает его путь."""
    temp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False,
        encoding="utf-8", newline="",
    )
    temp.write("\n".join(rows) + "\n")
    temp.close()
    return temp.name


def make_vfs(rows=None):
    """Создаёт VFS в памяти (файл сразу удаляется)."""
    path = write_csv(rows or CSV_ROWS)
    try:
        return VFS.from_csv(path)
    finally:
        os.unlink(path)


def make_session():
    """Создаёт состояние и параметры сессии."""
    return State(), Config("vfs.csv", "<none>")


def run(line, vfs=None):
    """Выполняет команду и возвращает результат."""
    state, config = make_session()
    return state, execute(line, state, config, vfs or make_vfs())


class VfsTest(unittest.TestCase):
    def test_root_listing(self):
        """Корень содержит home и motd."""
        vfs = make_vfs()
        state, config = make_session()
        result = execute("ls", state, config, vfs)
        self.assertEqual(result, "home  motd")

    def test_cd(self):
        """Переход в каталог меняет cwd."""
        vfs = make_vfs()
        state, config = make_session()
        execute("cd /home/user", state, config, vfs)
        self.assertEqual(state.cwd, "/home/user")

    def test_relative_cd(self):
        """Переход на уровень выше работает."""
        vfs = make_vfs()
        state, config = make_session()
        execute("cd /home/user", state, config, vfs)
        execute("cd ..", state, config, vfs)
        self.assertEqual(state.cwd, "/home")

    def test_nested_listing(self):
        """Список файлов вложенного каталога."""
        vfs = make_vfs()
        state, config = make_session()
        result = execute("ls /home/user/docs", state, config, vfs)
        self.assertEqual(result, "")

    def test_base64_content_loaded(self):
        """Данные из base64 раскодированы."""
        vfs = make_vfs()
        item = vfs.entries["/home/user/data.txt"]
        self.assertEqual(item.content, "Hello")

    def test_bad_cd(self):
        """Переход в несуществующий каталог дает ошибку."""
        vfs = make_vfs()
        state, config = make_session()
        with self.assertRaises(CommandError):
            execute("cd /missing", state, config, vfs)

    def test_unknown_command(self):
        """Неизвестная команда дает ошибку."""
        vfs = make_vfs()
        state, config = make_session()
        with self.assertRaises(CommandError):
            execute("unknown", state, config, vfs)

    def test_bad_arguments(self):
        """Лишние аргументы у ls дают ошибку."""
        vfs = make_vfs()
        state, config = make_session()
        with self.assertRaises(CommandError):
            execute("ls a b", state, config, vfs)

    def test_environment_variable(self):
        """Переменные окружения раскрываются."""
        os.environ["VFS_TEST_DIR"] = "/home"
        vfs = make_vfs()
        state, config = make_session()
        execute("cd $VFS_TEST_DIR", state, config, vfs)
        self.assertEqual(state.cwd, "/home")

    def test_history_lists_commands(self):
        """History нумерует команды сессии."""
        vfs = make_vfs()
        state, config = make_session()
        state.history.extend(["ls /", "cd /home"])
        result = execute("history", state, config, vfs)
        self.assertEqual(result, "1  ls /\n2  cd /home")

    def test_history_rejects_arguments(self):
        """History с аргументами дает ошибку."""
        vfs = make_vfs()
        state, config = make_session()
        with self.assertRaises(CommandError):
            execute("history x", state, config, vfs)

    def test_tail_defaults_to_last_lines(self):
        """Tail по умолчанию выводит конец файла."""
        vfs = make_vfs()
        state, config = make_session()
        result = execute("tail /home/user/log.txt", state, config, vfs)
        self.assertEqual(result, "a\nb\nc\nd")

    def test_tail_with_count(self):
        """Tail с -n выводит заданное число строк."""
        vfs = make_vfs()
        state, config = make_session()
        result = execute(
            "tail -n 2 /home/user/log.txt", state, config, vfs
        )
        self.assertEqual(result, "c\nd")

    def test_tail_missing_file(self):
        """Tail отсутствующего файла дает ошибку."""
        vfs = make_vfs()
        state, config = make_session()
        with self.assertRaises(CommandError):
            execute("tail /missing", state, config, vfs)

    def test_tail_directory(self):
        """Tail каталога дает ошибку."""
        vfs = make_vfs()
        state, config = make_session()
        with self.assertRaises(CommandError):
            execute("tail /home", state, config, vfs)

    def test_tail_bad_count(self):
        """Tail с нечисловым -n дает ошибку."""
        vfs = make_vfs()
        state, config = make_session()
        with self.assertRaises(CommandError):
            execute("tail -n abc /home/user/log.txt",
                    state, config, vfs)

    def test_tail_no_arguments(self):
        """Tail без аргументов дает ошибку."""
        vfs = make_vfs()
        state, config = make_session()
        with self.assertRaises(CommandError):
            execute("tail", state, config, vfs)

    def test_rm_file(self):
        """Rm удаляет файл из памяти."""
        vfs = make_vfs()
        state, config = make_session()
        execute("rm /home/user/log.txt", state, config, vfs)
        self.assertNotIn("/home/user/log.txt", vfs.entries)

    def test_rm_file_relative(self):
        """Rm понимает относительный путь."""
        vfs = make_vfs()
        state, config = make_session()
        execute("cd /home/user", state, config, vfs)
        execute("rm log.txt", state, config, vfs)
        self.assertNotIn("/home/user/log.txt", vfs.entries)

    def test_rm_empty_dir(self):
        """Rm удаляет пустой каталог."""
        vfs = make_vfs()
        state, config = make_session()
        execute("rm /home/user/docs", state, config, vfs)
        self.assertNotIn("/home/user/docs", vfs.entries)

    def test_rm_dir_without_flag(self):
        """Rm непустого каталога без -r дает ошибку."""
        vfs = make_vfs()
        state, config = make_session()
        with self.assertRaises(CommandError):
            execute("rm /home/user", state, config, vfs)

    def test_rm_dir_recursive(self):
        """Rm -r удаляет каталог с содержимым."""
        vfs = make_vfs()
        state, config = make_session()
        execute("rm -r /home/user", state, config, vfs)
        self.assertNotIn("/home/user", vfs.entries)
        self.assertNotIn("/home/user/log.txt", vfs.entries)

    def test_rm_missing(self):
        """Rm отсутствующего файла дает ошибку."""
        vfs = make_vfs()
        state, config = make_session()
        with self.assertRaises(CommandError):
            execute("rm /missing", state, config, vfs)

    def test_rm_no_arguments(self):
        """Rm без аргументов дает ошибку."""
        vfs = make_vfs()
        state, config = make_session()
        with self.assertRaises(CommandError):
            execute("rm", state, config, vfs)

    def test_rm_root_denied(self):
        """Rm корня запрещен."""
        vfs = make_vfs()
        state, config = make_session()
        with self.assertRaises(CommandError):
            execute("rm -r /", state, config, vfs)

    def test_rm_resets_cwd(self):
        """После удаления текущего каталога cwd в корне."""
        vfs = make_vfs()
        state, config = make_session()
        execute("cd /home/user", state, config, vfs)
        execute("rm -r /home/user", state, config, vfs)
        self.assertEqual(state.cwd, "/")

    def test_rm_extra_arguments(self):
        """Rm с лишними аргументами дает ошибку."""
        vfs = make_vfs()
        state, config = make_session()
        with self.assertRaises(CommandError):
            execute("rm a b", state, config, vfs)


if __name__ == "__main__":
    unittest.main()
