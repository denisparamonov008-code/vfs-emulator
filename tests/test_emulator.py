"""Тесты эмулятора: VFS и команды этапов 1-3."""

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
    "file,/motd,Hello,plain",
    "file,/home/user/data.txt,SGVsbG8=,base64",
]


def write_csv(rows):
    """Пишет временный CSV и возвращает путь к нему."""
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
        result = execute("ls /home/user", state, config, vfs)
        self.assertEqual(result, "data.txt")

    def test_base64_content_loaded(self):
        """Данные из base64 раскодированы."""
        vfs = make_vfs()
        item = vfs.entries["/home/user/data.txt"]
        self.assertEqual(item.content, "Hello")

    def test_motd_loaded(self):
        """Файл motd читается из VFS."""
        vfs = make_vfs()
        self.assertEqual(vfs.entries["/motd"].content, "Hello")

    def test_parent_dirs_created(self):
        """Родительские каталоги создаются автоматически."""
        rows = [
            "type,path,content,encoding",
            "file,/a/b/c/file.txt,text,plain",
        ]
        vfs = make_vfs(rows)
        self.assertIn("/a", vfs.entries)
        self.assertIn("/a/b", vfs.entries)
        self.assertIn("/a/b/c", vfs.entries)

    def test_bad_csv_format(self):
        """Неверный формат CSV дает ошибку."""
        rows = ["path,content", "/motd,Hello"]
        with self.assertRaises(RuntimeError):
            make_vfs(rows)

    def test_missing_vfs_file(self):
        """Отсутствующий файл VFS дает ошибку."""
        with self.assertRaises(RuntimeError):
            VFS.from_csv("/tmp/vfs_no_such_file.csv")

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


if __name__ == "__main__":
    unittest.main()
