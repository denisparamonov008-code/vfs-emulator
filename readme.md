# Эмулятор UNIX-оболочки (вариант 26)

Учебный проект по дисциплине «Конфигурационное управление».

## Описание

Эмулятор командной строки UNIX с виртуальной файловой системой (VFS)
в памяти и графическим интерфейсом в стиле терминала.

Возможности:
- GUI на Tkinter — тёмное окно, зелёное приглашение, красные ошибки.
- VFS загружается из CSV-файла.
- Запуск стартового скрипта при старте.
- Работает на Windows, macOS и Linux.

## Команды

- `ls` — список файлов в каталоге
- `cd` — сменить каталог
- `history` — история команд
- `tail` — последние строки файла
- `rm [-r]` — удалить файл или каталог
- `conf-dump` — показать параметры эмулятора
- `help` — справка
- `exit` — выход

## Запуск

Требуется Python 3.8+ с модулем `tkinter`.

    python3 emulator.py
    python3 emulator.py --vfs vfs.csv
    python3 emulator.py --vfs vfs.csv --script startup.sh

## Формат CSV для VFS

    type,path,content,encoding
    dir,/,,
    dir,/home,,
    file,/home/notes.txt,строка 1,,plain

- `type` — `dir` или `file`
- `path` — абсолютный путь внутри VFS
- `content` — содержимое файла
- `encoding` — `plain` или `base64`

## Пример работы

    vfs:/$ ls
    home/
    motd
    vfs:/$ cd home
    vfs:/home$ tail notes.txt
    строка 3

## Автор

Стрельников Иван, ИКБО-23-25
