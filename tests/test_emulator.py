"""Тесты прототипа REPL первого этапа."""

import io
import os
import unittest
from contextlib import redirect_stdout

from src.emulator import execute


def run(line):
    """Выполняет команду и возвращает статус и вывод."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            execute(line)
        except SystemExit:
            return "exit", buf.getvalue()
    return "ok", buf.getvalue()


class StubTest(unittest.TestCase):
    def test_ls_stub(self):
        """Заглушка ls печатает имя и аргументы."""
        status, out = run("ls /tmp")
        self.assertEqual(status, "ok")
        self.assertEqual(out.strip(), "ls /tmp")

    def test_cd_stub(self):
        """Заглушка cd печатает имя и аргументы."""
        status, out = run("cd /tmp")
        self.assertEqual(status, "ok")
        self.assertEqual(out.strip(), "cd /tmp")

    def test_help(self):
        """Справка перечисляет команды."""
        status, out = run("help")
        self.assertEqual(status, "ok")
        self.assertIn("ls", out)
        self.assertIn("exit", out)

    def test_unknown(self):
        """Неизвестная команда дает ошибку."""
        status, out = run("bogus")
        self.assertEqual(status, "ok")
        self.assertIn("неизвестная команда", out)

    def test_exit(self):
        """Команда exit завершает работу."""
        status, _out = run("exit")
        self.assertEqual(status, "exit")

    def test_exit_with_args(self):
        """Exit с аргументами дает ошибку."""
        status, out = run("exit now")
        self.assertEqual(status, "ok")
        self.assertIn("использование", out)

    def test_empty_line(self):
        """Пустая строка ничего не выводит."""
        status, out = run("   ")
        self.assertEqual(status, "ok")
        self.assertEqual(out, "")

    def test_env_expansion(self):
        """Переменные окружения раскрываются."""
        os.environ["VFS_TEST_VAR"] = "myval"
        status, out = run("ls $VFS_TEST_VAR")
        self.assertEqual(status, "ok")
        self.assertEqual(out.strip(), "ls myval")


if __name__ == "__main__":
    unittest.main()
