
import argparse, csv, os, platform, posixpath, shlex, traceback
import tkinter as tk
from tkinter import font as tkfont


# ---------- ошибки ----------
class CmdError(Exception):
    pass


# ---------- VFS ----------
class VFS:
    """Виртуальная ФС в памяти: {путь: {type, content, encoding}}."""

    def __init__(self, name="vfs"):
        self.name = name
        self.nodes = {}
        self.add_dir("/")
        self.add_dir("/home")
        self.add_dir("/home/user")
        self.add_file("/motd", "Привет! Введи help для списка команд.\n")
        self.add_file("/home/user/notes.txt", "один\nдва\nтри\n")
        self.add_file("/home/user/data.bin", "SGVsbG8=", encoding="base64")

    def add_dir(self, path):
        path = self._abs(path)
        if path != "/":
            self.add_dir(posixpath.dirname(path))
        self.nodes[path] = {"type": "dir", "content": "", "encoding": "plain"}

    def add_file(self, path, content="", encoding="plain"):
        path = self._abs(path)
        self.add_dir(posixpath.dirname(path))
        self.nodes[path] = {"type": "file", "content": content, "encoding": encoding}

    def _abs(self, path):
        if not path.startswith("/"):
            path = "/" + path
        return posixpath.normpath(path)

    def exists(self, p):
        return self._abs(p) in self.nodes

    def is_dir(self, p):
        return self.nodes.get(self._abs(p), {}).get("type") == "dir"

    def load_csv(self, path):
        """Загрузка VFS из CSV: колонки type,path,content[,encoding]."""
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        self.nodes = {}
        self.add_dir("/")
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                t, p = row["type"].strip(), row["path"].strip()
                if t == "dir":
                    self.add_dir(p)
                else:
                    self.add_file(p, row.get("content", ""), row.get("encoding", "plain"))


# ---------- команды ----------
def cmd_ls(a, vfs, st):
    target = vfs._abs(a[0] if a else st["cwd"])
    if not vfs.exists(target):
        raise CmdError("нет такого файла или каталога")
    if not vfs.is_dir(target):
        return posixpath.basename(target)
    prefix = "/" if target == "/" else target + "/"
    names = {}
    for p, n in vfs.nodes.items():
        if p.startswith(prefix) and p != target:
            rest = p[len(prefix):]
            key = rest.split("/")[0]
            names[key] = "dir" if "/" in rest else n["type"]
    if not names:
        return ""
    return "\n".join(sorted(k + ("/" if t == "dir" else "") for k, t in names.items()))


def cmd_cd(a, vfs, st):
    if not a:
        st["cwd"] = "/"
        return ""
    p = vfs._abs(posixpath.join(st["cwd"], a[0]))
    if not vfs.exists(p):
        raise CmdError("нет такого каталога")
    if not vfs.is_dir(p):
        raise CmdError("не каталог")
    st["cwd"] = p
    return ""


def cmd_history(a, vfs, st):
    if not st["history"]:
        return ""
    return "\n".join(f"{i:4}  {c}" for i, c in enumerate(st["history"], 1))


def cmd_tail(a, vfs, st):
    if not a:
        raise CmdError("использование: tail файл")
    p = vfs._abs(posixpath.join(st["cwd"], a[-1]))
    if not vfs.exists(p) or vfs.is_dir(p):
        raise CmdError("нет такого файла")
    if vfs.nodes[p]["encoding"] == "base64":
        raise CmdError("бинарный файл, tail не поддерживается")
    return "\n".join(vfs.nodes[p]["content"].splitlines()[-10:])


def cmd_rm(a, vfs, st):
    rec = bool(a) and a[0] == "-r"
    if rec:
        a = a[1:]
    if not a:
        raise CmdError("использование: rm [-r] путь")
    p = vfs._abs(posixpath.join(st["cwd"], a[0]))
    if p == "/" or not vfs.exists(p):
        raise CmdError("нельзя удалить")
    if vfs.is_dir(p):
        kids = [x for x in vfs.nodes if x.startswith(p + "/")]
        if kids and not rec:
            raise CmdError("каталог не пуст (используйте -r)")
        for x in kids:
            del vfs.nodes[x]
    del vfs.nodes[p]
    return ""


def cmd_conf_dump(a, vfs, st):
    items = {
        "vfs_name": vfs.name,
        "vfs_path": st["config"]["vfs_path"],
        "script_path": st["config"]["script_path"],
        "cwd": st["cwd"],
    }
    return "\n".join(f"{k}={v}" for k, v in items.items())


def cmd_help(a, vfs, st):
    lines = [
        "ls         список файлов в каталоге",
        "cd         сменить каталог",
        "history    история команд",
        "tail       последние строки файла",
        "rm [-r]    удалить файл или каталог",
        "conf-dump  показать параметры эмулятора",
        "help       эта справка",
        "exit       выход",
    ]
    return "\n".join(lines)


COMMANDS = {
    "ls": cmd_ls, "cd": cmd_cd, "history": cmd_history,
    "tail": cmd_tail, "rm": cmd_rm, "conf-dump": cmd_conf_dump, "help": cmd_help,
}


def run(cmd_line, vfs, st):
    """Выполняет одну строку, возвращает вывод."""
    tokens = [os.path.expandvars(t) for t in shlex.split(cmd_line)]
    if not tokens:
        return ""
    if tokens[0] == "exit":
        raise SystemExit
    if tokens[0] not in COMMANDS:
        raise CmdError(f"неизвестная команда: {tokens[0]}")
    return COMMANDS[tokens[0]](tokens[1:], vfs, st)


# ---------- окно терминала ----------
class Terminal:
    def __init__(self, root, vfs, st, motd=None, script=None):
        self.root, self.vfs, self.st = root, vfs, st

        root.title(f"Эмулятор - {vfs.name}")
        root.geometry("900x550")            # явный размер — иначе на macOS окно «нулевое»
        root.minsize(600, 350)
        if platform.system() != "Darwin":
            root.configure(bg="#0c0c0c")

        # моноширинный шрифт под платформу
        if platform.system() == "Windows":
            family = "Consolas"
        elif platform.system() == "Darwin":
            family = "Menlo"
        else:
            family = "DejaVu Sans Mono"
        try:
            mono = tkfont.Font(family=family, size=12)
        except tk.TclError:
            mono = tkfont.Font(family="Courier", size=12)

        self.text = tk.Text(
            root,
            bg="#0c0c0c", fg="#d0d0d0",
            insertbackground="#d0d0d0",
            font=mono, wrap="word",
            borderwidth=0, highlightthickness=0,
            padx=10, pady=8,
        )
        self.text.pack(fill="both", expand=True)

        self.text.tag_configure("prompt", foreground="#39d353")
        self.text.tag_configure("error", foreground="#ff5f56")
        self.text.bind("<Return>", self.on_enter)
        self.text.bind("<Button-1>", lambda e: self.text.focus_set())

        # фокус — важно для macOS, особенно с Tk 8.5
        self.text.focus_set()
        root.after(50, self.text.focus_force)

        # прокрутка
        sb = tk.Scrollbar(root, command=self.text.yview)
        sb.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=sb.set)

        if motd:
            self.print_line(motd)
        if script:
            for line in script:
                self.print_line(self.prompt_str() + line)
                try:
                    out = run(line, vfs, st)
                    if out:
                        self.print_line(out)
                except CmdError as e:
                    self.print_line(f"error: {e}", "error")
        self.new_prompt()

    def prompt_str(self):
        return f"{self.vfs.name}:{self.st['cwd']}$ "

    def print_line(self, txt, tag=None):
        self.text.insert("end", txt + "\n", tag or ())
        self.text.see("end")

    def new_prompt(self):
        self.text.insert("end", self.prompt_str(), ("prompt",))
        self.text.mark_set("insert", "end")
        self.text.see("end")

    def on_enter(self, event):
        # берём только последнюю строку — то, что ввёл пользователь
        line = self.text.get("end-1c linestart", "end-1c")
        prompt = self.prompt_str()
        if line.startswith(prompt):
            line = line[len(prompt):]
        self.print_line("")
        if line.strip():
            self.st["history"].append(line)
        try:
            out = run(line, self.vfs, self.st)
            if out:
                self.print_line(out)
        except CmdError as e:
            self.print_line(f"error: {e}", "error")
        except SystemExit:
            self.root.destroy()
            return "break"
        self.new_prompt()
        return "break"


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vfs", help="путь к CSV-файлу VFS")
    ap.add_argument("--script", help="путь к стартовому скрипту")
    args = ap.parse_args()

    name = os.path.splitext(os.path.basename(args.vfs))[0] if args.vfs else "vfs"
    vfs = VFS(name)
    if args.vfs:
        try:
            vfs.load_csv(args.vfs)
        except Exception as e:
            print("ошибка загрузки VFS:", e)

    st = {
        "cwd": "/",
        "history": [],
        "config": {
            "vfs_path": args.vfs or "<memory>",
            "script_path": args.script or "<none>",
        },
    }

    script_lines = []
    if args.script and os.path.exists(args.script):
        with open(args.script, encoding="utf-8") as f:
            script_lines = [
                l.strip() for l in f
                if l.strip() and not l.strip().startswith("#")
            ]

    root = tk.Tk()
    try:
        Terminal(root, vfs, st,
                 motd=vfs.nodes.get("/motd", {}).get("content"),
                 script=script_lines)
        root.mainloop()
    except Exception:
        traceback.print_exc()
        root.destroy()


if __name__ == "__main__":
    main()
