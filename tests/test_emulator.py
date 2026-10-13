"""Тесты настраиваемого эмулятора второго этапа."""

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from src.emulator import Config, execute, run_script


def make_config():
    """Создаёт параметры запуска для тестов."""
    return Config("vfs.csv", "<none>")


def run(line, config):
    """Выполняет команду и возвращает статус и вывод."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            execute(line, config)
        except SystemExit:
            return "exit", buf.getvalue()
    return "ok", buf.getvalue()


def make_temp_script(text):
    """Создаёт временный стартовый скрипт."""
    temp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    )
    temp.write(text)
    temp.close()
    return temp.name


class ConfigTest(unittest.TestCase):
    def test_conf_dump(self):
        """Conf-dump печатает параметры запуска."""
        status, out = run("conf-dump", make_config())
        self.assertEqual(status, "ok")
        self.assertIn("vfs_path=vfs.csv", out)
        self.assertIn("script_path=<none>", out)

    def test_conf_dump_with_args(self):
        """Conf-dump с аргументами дает ошибку."""
        status, out = run("conf-dump x", make_config())
        self.assertEqual(status, "ok")
        self.assertIn("использование", out)

    def test_ls_stub(self):
        """Заглушка ls печатает имя и аргументы."""
        status, out = run("ls /tmp", make_config())
        self.assertEqual(status, "ok")
        self.assertEqual(out.strip(), "ls /tmp")

    def test_cd_stub(self):
        """Заглушка cd печатает имя и аргументы."""
        status, out = run("cd /tmp", make_config())
        self.assertEqual(status, "ok")
        self.assertEqual(out.strip(), "cd /tmp")

    def test_unknown(self):
        """Неизвестная команда дает ошибку."""
        status, out = run("bogus", make_config())
        self.assertEqual(status, "ok")
        self.assertIn("неизвестная команда", out)

    def test_exit(self):
        """Команда exit завершает работу."""
        status, _out = run("exit", make_config())
        self.assertEqual(status, "exit")

    def test_exit_with_args(self):
        """Exit с аргументами дает ошибку."""
        status, out = run("exit now", make_config())
        self.assertEqual(status, "ok")
        self.assertIn("использование", out)

    def test_env_expansion(self):
        """Переменные окружения раскрываются."""
        os.environ["VFS_TEST_VAR"] = "myval"
        status, out = run("ls $VFS_TEST_VAR", make_config())
        self.assertEqual(status, "ok")
        self.assertEqual(out.strip(), "ls myval")

    def test_script_runs_commands(self):
        """Стартовый скрипт выполняет команды."""
        path = make_temp_script("help\n")
        try:
            stopped = run_script(path, make_config())
            self.assertFalse(stopped)
        finally:
            os.unlink(path)

    def test_script_stops_on_exit(self):
        """Скрипт останавливается после exit."""
        path = make_temp_script("exit\n")
        try:
            stopped = run_script(path, make_config())
            self.assertTrue(stopped)
        finally:
            os.unlink(path)

    def test_script_missing_file(self):
        """Несуществующий скрипт дает ошибку."""
        stopped = run_script("/tmp/vfs_no_such_script.txt",
                             make_config())
        self.assertTrue(stopped)


if __name__ == "__main__":
    unittest.main()
