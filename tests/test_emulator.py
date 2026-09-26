import os
import tempfile
import unittest

from src.emulator import Config, State, VFS, execute


class VfsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8", newline="")
        self.temp.write("type,path,content,encoding\n")
        self.temp.write("dir,/, ,plain\n")
        self.temp.write("dir,/home,,plain\n")
        self.temp.write("dir,/home/user,,plain\n")
        self.temp.write("file,/motd,Hello,plain\n")
        self.temp.write("file,/home/user/data.txt,SGVsbG8=,base64\n")
        self.temp.close()
        self.vfs = VFS.from_csv(self.temp.name)
        self.state = State()
        self.config = Config(self.temp.name, "<none>")

    def tearDown(self):
        os.unlink(self.temp.name)

    def test_root_listing(self):
        self.assertEqual(execute("ls", self.state, self.config, self.vfs), "home  motd")

    def test_cd(self):
        execute("cd /home/user", self.state, self.config, self.vfs)
        self.assertEqual(self.state.cwd, "/home/user")

    def test_relative_cd(self):
        execute("cd /home/user", self.state, self.config, self.vfs)
        execute("cd ..", self.state, self.config, self.vfs)
        self.assertEqual(self.state.cwd, "/home")

    def test_nested_listing(self):
        result = execute("ls /home/user", self.state, self.config, self.vfs)
        self.assertEqual(result, "data.txt")

    def test_base64_content_loaded(self):
        self.assertEqual(self.vfs.entries["/home/user/data.txt"].content, "Hello")

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


if __name__ == "__main__":
    unittest.main()
