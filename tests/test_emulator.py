import os
import tempfile
import unittest

from src.emulator import Config, State, VFS, VfsEntry, execute


def make_csv():
    """Создаёт временный CSV для тестов."""
    temp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False,
        encoding="utf-8", newline="",
    )
    temp.write("type,path,content,encoding\n")
    temp.write("dir,/, ,plain\n")
    temp.write("dir,/home,,plain\n")
    temp.write("dir,/home/user,,plain\n")
    temp.write("file,/motd,Hello,plain\n")
    temp.write("file,/home/user/data.txt,SGVsbG8=,base64\n")
    temp.close()
    return temp.name


class VfsTest(unittest.TestCase):
    def setUp(self):
        self.path = make_csv()
        self.vfs = VFS.from_csv(self.path)
        self.state = State()
        self.config = Config(self.path, "<none>")

    def tearDown(self):
        os.unlink(self.path)

    def test_root_listing(self):
        result = execute("ls", self.state, self.config, self.vfs)
        self.assertEqual(result, "home  motd")

    def test_cd(self):
        execute("cd /home/user", self.state, self.config, self.vfs)
        self.assertEqual(self.state.cwd, "/home/user")

    def test_relative_cd(self):
        execute("cd /home/user", self.state, self.config, self.vfs)
        execute("cd ..", self.state, self.config, self.vfs)
        self.assertEqual(self.state.cwd, "/home")

    def test_nested_listing(self):
        result = execute(
            "ls /home/user", self.state, self.config, self.vfs
        )
        self.assertEqual(result, "data.txt")

    def test_base64_content_loaded(self):
        item = self.vfs.entries["/home/user/data.txt"]
        self.assertEqual(item.content, "Hello")

    def test_bad_cd(self):
        with self.assertRaises(Exception):
            execute("cd /missing", self.state, self.config, self.vfs)

    def test_unknown_command(self):
        with self.assertRaises(Exception):
            execute("unknown", self.state, self.config, self.vfs)

    def test_bad_arguments(self):
        with self.assertRaises(Exception):
            execute("ls a b", self.state, self.config, self.vfs)

    def test_environment_variable(self):
        os.environ["VFS_TEST_DIR"] = "/home"
        execute("cd $VFS_TEST_DIR", self.state, self.config, self.vfs)
        self.assertEqual(self.state.cwd, "/home")

    def test_history_lists_commands(self):
        self.state.history.extend(["ls /", "cd /home"])
        result = execute(
            "history", self.state, self.config, self.vfs
        )
        self.assertEqual(result, "1  ls /\n2  cd /home")

    def test_history_rejects_arguments(self):
        with self.assertRaises(Exception):
            execute("history x", self.state, self.config, self.vfs)

    def test_tail_defaults_to_last_lines(self):
        self.vfs.entries["/log.txt"] = VfsEntry(
            "/log.txt", "file", "a\nb\nc"
        )
        result = execute(
            "tail /log.txt", self.state, self.config, self.vfs
        )
        self.assertEqual(result, "a\nb\nc")

    def test_tail_with_count(self):
        self.vfs.entries["/log.txt"] = VfsEntry(
            "/log.txt", "file", "a\nb\nc\nd"
        )
        result = execute(
            "tail -n 2 /log.txt", self.state, self.config, self.vfs
        )
        self.assertEqual(result, "c\nd")

    def test_tail_missing_file(self):
        with self.assertRaises(Exception):
            execute("tail /missing", self.state, self.config, self.vfs)

    def test_tail_directory(self):
        with self.assertRaises(Exception):
            execute("tail /home", self.state, self.config, self.vfs)

    def test_tail_bad_count(self):
        self.vfs.entries["/log.txt"] = VfsEntry(
            "/log.txt", "file", "a\nb"
        )
        with self.assertRaises(Exception):
            execute(
                "tail -n abc /log.txt",
                self.state,
                self.config,
                self.vfs,
            )

    def test_tail_no_arguments(self):
        with self.assertRaises(Exception):
            execute("tail", self.state, self.config, self.vfs)


if __name__ == "__main__":
    unittest.main()
