## Скрипт: deepest_paths.py — поиск самых глубоких директорий

Показывает топ N директорий с максимальной глубиной вложенности (или по длине полного пути) относительно заданного корня.

### Требования

- Python 3.8+

### Установка

В каталоге проекта уже есть `deepest_paths.py`. Устанавливать ничего не нужно.

### Запуск

#### Windows (PowerShell)

```powershell
python .\deepest_paths.py "D:\Code_and_Scripts_local\for_work\folder_depth" --top 10
```

#### macOS / Linux (bash/zsh)

```bash
python3 deepest_paths.py "/path/to/root" --top 10
```

### Опции

- `path` (позиционный): корневая директория, от которой считаем вложенность.
- `--top N`: сколько самых глубоких путей вывести (по умолчанию 1).
- `--by-length`: сортировать по длине полного пути, а не по глубине.
- `--follow-symlinks`: следовать симлинкам.
- `--out PATH`: сохранить результат в файл (если не указан — только консольный вывод).
- `--out-format {txt|csv|json}`: формат файла вывода (по умолчанию `txt`).

### Примеры

- Топ-1 по глубине (по умолчанию):

```bash
python3 deepest_paths.py "/path/to/root"
python3 deepest_paths.py "D:\IDC DOO\Docs - Design"
```

- Топ-10 по глубине:

```bash
python3 deepest_paths.py "/path/to/root" --top 10
```

- Топ-5 по длине полного пути:

```bash
python3 deepest_paths.py "/path/to/root" --top 5 --by-length
```

- С учетом симлинков:

```bash
python3 deepest_paths.py "/path/to/root" --follow-symlinks
```

- Запись результата в файл:

```powershell
# TXT
python .\deepest_paths.py "D:\IDC DOO\Docs - Design" --top 10 --out .\out\deepest.txt

# CSV
python .\deepest_paths.py "D:\IDC DOO\Docs - Design" --top 10 --out .\out\deepest.csv --out-format csv

# JSON
python .\deepest_paths.py "D:\IDC DOO\Docs - Design" --top 10 --out .\out\deepest.json --out-format json
```

### Вывод

Для каждого результата выводятся:

- `depth` — глубина вложенности относительно базы,
- `len` — длина полного пути,
- полный путь директории.

Пример:

```text
Base: /path/to/root
Sort mode: depth

#1: depth=7, len=64
/path/to/root/a/b/c/d/e/f/g
```

### Кириллица в консоли Windows

Скрипт сам переключает кодировку консоли на UTF‑8. Если в выводе всё ещё появляются `?`, принудительно выполните в текущей сессии PowerShell перед запуском:

```powershell
chcp 65001 > $null; $env:PYTHONIOENCODING="UTF-8"
```

### Длинные пути в Windows (>260 символов)

Скрипт использует расширенные префиксы путей (`\\?\`, `\\?\UNC\...`) внутри обхода, поэтому корректно обрабатывает пути длиннее 260 символов. При необходимости можно явно передать путь с префиксом:

```powershell
python .\deepest_paths.py "\\?\D:\IDC DOO\Docs - Design" --top 10
```

Рекомендуется включить поддержку длинных путей в политике системы (Enable Win32 long paths) для совместимости с другими инструментами.

#### Примеры с длинными путями

```powershell
# Локальный путь с префиксом \\?\ (длинные пути)
python .\deepest_paths.py "\\?\D:\Очень_длинный_каталог\...\ещё\глубже\и_дальше" --top 15

# Локальный путь + сохранение результата в TXT
python .\deepest_paths.py "\\?\D:\Очень_длинный_каталог\...\ещё\глубже\и_дальше" --top 20 --out .\out\deepest_long.txt

# Локальный путь + CSV
python .\deepest_paths.py "\\?\D:\Очень_длинный_каталог\...\ещё\глубже\и_дальше" --top 50 --out .\out\deepest_long.csv --out-format csv

# Локальный путь + JSON и сортировка по длине полного пути
python .\deepest_paths.py "\\?\D:\Очень_длинный_каталог\...\ещё\глубже\и_дальше" --top 50 --by-length --out .\out\deepest_long.json --out-format json

# UNC-шара: \\сервер\шара -> \\?\UNC\сервер\шара
python .\deepest_paths.py "\\?\UNC\fileserver\share\Очень_длинный_путь\..." --top 25

# UNC + сохранение результата
python .\deepest_paths.py "\\?\UNC\fileserver\share\Очень_длинный_путь\..." --top 25 --out .\out\deepest_unc.csv --out-format csv
```
