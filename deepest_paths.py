#!/usr/bin/env python3
import argparse
import os
import json
import csv
from typing import List, Tuple


def _is_windows() -> bool:
    return os.name == "nt"


def _to_extended_path(path: str) -> str:
    if not _is_windows():
        return path
    # Already extended
    if path.startswith("\\\\?\\"):
        return path
    # UNC path \\server\share -> \\?\UNC\server\share
    if path.startswith("\\\\"):
        return "\\\\?\\UNC\\" + path.lstrip("\\")
    # Drive path C:\...
    return "\\\\?\\" + path


def _from_extended_path(path: str) -> str:
    if not _is_windows():
        return path
    if path.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path[len("\\\\?\\UNC\\") :]
    if path.startswith("\\\\?\\"):
        return path[len("\\\\?\\") :]
    return path


def compute_depth(base_path: str, target_path: str) -> int:
    base = base_path.rstrip(os.sep)
    target = target_path.rstrip(os.sep)
    # Normalize multiple separators and resolve relative parts
    base = os.path.abspath(base)
    target = os.path.abspath(target)
    base_parts = [p for p in base.split(os.sep) if p]
    target_parts = [p for p in target.split(os.sep) if p]
    # Depth is number of extra components beyond base
    return max(0, len(target_parts) - len(base_parts))


def walk_directories(root: str, follow_symlinks: bool) -> List[str]:
    collected: List[str] = []
    base_normal = os.path.abspath(root)
    base_for_walk = _to_extended_path(base_normal) if _is_windows() else base_normal
    # Always include the root itself for completeness
    collected.append(base_normal)
    for dirpath, dirnames, _filenames in os.walk(
        base_for_walk, followlinks=follow_symlinks
    ):
        # Convert back to display-normalized path for scoring and output
        disp = _from_extended_path(dirpath)
        abs_dir = os.path.abspath(disp)
        collected.append(abs_dir)
    # De-duplicate while preserving order (in case os.walk yields root twice)
    seen = set()
    unique: List[str] = []
    for p in collected:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def find_deepest(
    root: str,
    top_k: int,
    by_length: bool,
    follow_symlinks: bool,
) -> List[Tuple[int, int, str]]:
    dirs = walk_directories(root, follow_symlinks)
    scored: List[Tuple[int, int, str]] = []  # (depth, path_len, path)
    for d in dirs:
        try:
            depth = compute_depth(root, d)
        except Exception:
            # If weird path encoding or access error in compute, skip
            continue
        scored.append((depth, len(d), d))

    if by_length:
        # First by path length desc, then by depth desc, then lexicographically
        scored.sort(key=lambda t: (t[1], t[0], t[2]), reverse=True)
    else:
        # First by depth desc, then by path length desc, then lexicographically
        scored.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)

    return scored[: max(1, top_k)]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Показывает самые глубокие директории (топ N) относительно заданного корня."
        )
    )
    parser.add_argument(
        "path",
        help="Путь к корневой директории, от которой считать вложенность",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=1,
        help="Сколько самых глубоких путей показать (по умолчанию 1)",
    )
    parser.add_argument(
        "--by-length",
        action="store_true",
        help="Сортировать по длине полного пути (а не по глубине вложенности)",
    )
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Следовать по симлинкам (по умолчанию не следуем)",
    )
    parser.add_argument(
        "--out",
        help="Путь к файлу для сохранения результата (если не указан — только вывод в консоль)",
    )
    parser.add_argument(
        "--out-format",
        choices=["txt", "csv", "json"],
        default="txt",
        help="Формат файла вывода: txt | csv | json (по умолчанию txt)",
    )

    args = parser.parse_args()
    # Ensure Cyrillic output on Windows consoles by switching to UTF-8
    try:
        import sys
        if os.name == "nt":
            try:
                import ctypes  # type: ignore
                kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
                kernel32.SetConsoleOutputCP(65001)  # UTF-8
                kernel32.SetConsoleCP(65001)
            except Exception:
                pass
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="strict")
            except Exception:
                try:
                    sys.stdout.reconfigure(errors="replace")
                except Exception:
                    pass
            try:
                sys.stderr.reconfigure(encoding="utf-8", errors="strict")
            except Exception:
                try:
                    sys.stderr.reconfigure(errors="replace")
                except Exception:
                    pass
    except Exception:
        pass
    root = os.path.abspath(args.path)

    # Existence checks with extended prefix fallback on Windows
    if not os.path.exists(root):
        if _is_windows() and os.path.exists(_to_extended_path(root)):
            pass
        else:
            raise SystemExit(f"Путь не существует: {root}")
    if not os.path.isdir(root):
        if _is_windows() and os.path.isdir(_to_extended_path(root)):
            pass
        else:
            raise SystemExit(f"Это не директория: {root}")

    results = find_deepest(
        root=root,
        top_k=args.top,
        by_length=args.by_length,
        follow_symlinks=args.follow_symlinks,
    )

    mode = "path length" if args.by_length else "depth"
    print(f"Base: {root}")
    print(f"Sort mode: {mode}")
    print()
    for rank, (depth, plen, path) in enumerate(results, start=1):
        print(f"#{rank}: depth={depth}, len={plen}")
        print(path)
        print()

    # Optional file output
    if args.out:
        out_path = os.path.abspath(args.out)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        if args.out_format == "txt":
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(f"Base: {root}\n")
                f.write(f"Sort mode: {mode}\n\n")
                for rank, (depth, plen, path) in enumerate(results, start=1):
                    f.write(f"#{rank}: depth={depth}, len={plen}\n")
                    f.write(f"{path}\n\n")
        elif args.out_format == "csv":
            with open(out_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["rank", "depth", "path_length", "path"]) 
                for rank, (depth, plen, path) in enumerate(results, start=1):
                    writer.writerow([rank, depth, plen, path])
        else:  # json
            json_payload = [
                {"rank": rank, "depth": depth, "path_length": plen, "path": path}
                for rank, (depth, plen, path) in enumerate(results, start=1)
            ]
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "base": root,
                        "sort_mode": mode,
                        "items": json_payload,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        print(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()


