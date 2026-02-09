#!/usr/bin/env python3
import argparse
import os
import json
import csv
import datetime
from typing import List, Tuple, Dict, Any


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


def scan_directory_tree(root: str, follow_symlinks: bool, max_depth: int) -> Dict[str, Any]:
    """Рекурсивно сканирует дерево, собирая размеры и структуру с применением лимита глубины."""
    root_abs = os.path.abspath(root)
    root_ext = _to_extended_path(root_abs) if _is_windows() else root_abs
    
    def _scan(path_ext, path_display, depth):
        total_size = 0
        children = []
        
        # Если превышена глубина, сканируем только файлы для размера, но не идем глубже по папкам
        can_go_deeper = depth < max_depth
        
        try:
            with os.scandir(path_ext) as it:
                for entry in it:
                    try:
                        if entry.is_file(follow_symlinks=follow_symlinks):
                            total_size += entry.stat(follow_symlinks=follow_symlinks).st_size
                        elif entry.is_dir(follow_symlinks=follow_symlinks):
                            if can_go_deeper:
                                child_tree = _scan(entry.path, os.path.join(path_display, entry.name), depth + 1)
                                total_size += child_tree["s"]
                                children.append(child_tree)
                            else:
                                # Просто считаем размер вложенной папки, не сохраняя её структуру
                                total_size += _get_dir_size(entry.path, follow_symlinks)
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            pass
            
        children.sort(key=lambda x: x["n"])
        return {
            "n": os.path.basename(path_display) or path_display,
            "p": os.path.relpath(path_display, root_abs) if path_display != root_abs else ".",
            "s": total_size,
            "d": depth,
            "c": children
        }

    def _get_dir_size(path_ext, follow_symlinks):
        size = 0
        try:
            with os.scandir(path_ext) as it:
                for entry in it:
                    try:
                        if entry.is_file(follow_symlinks=follow_symlinks):
                            size += entry.stat(follow_symlinks=follow_symlinks).st_size
                        elif entry.is_dir(follow_symlinks=follow_symlinks):
                            size += _get_dir_size(entry.path, follow_symlinks)
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            pass
        return size

    return _scan(root_ext, root_abs, 0)


def flatten_tree(node: Dict[str, Any], root_abs: str) -> List[Dict[str, Any]]:
    """Превращает дерево обратно в плоский список с восстановлением путей."""
    # Восстанавливаем полный путь для совместимости
    p = node["p"]
    abs_p = os.path.abspath(os.path.join(root_abs, p)) if p != "." else root_abs
    
    res = [{
        "name": node["n"],
        "path": abs_p,
        "size": node["s"],
        "depth": node["d"]
    }]
    for child in node.get("c", []):
        res.extend(flatten_tree(child, root_abs))
    return res


def generate_html_report(root: str, tree: Dict[str, Any], results: List[Tuple[int, int, str, int]]) -> str:
    """Генерирует стильный самодостаточный HTML-отчет."""
    json_tree = json.dumps(tree, ensure_ascii=False)
    json_results = json.dumps([
        {"rank": i+1, "depth": d, "len": l, "path": p, "size": s} 
        for i, (d, l, p, s) in enumerate(results)
    ], ensure_ascii=False)
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    template = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Folder Structure Report - {os.path.basename(root)}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #6366f1;
            --secondary: #10b981;
            --bg: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --border: rgba(255, 255, 255, 0.1);
            --text: #f1f5f9;
            --text-dim: #94a3b8;
        }}
        body {{
            background: var(--bg);
            color: var(--text);
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 2rem;
            line-height: 1.5;
        }}
        .glass {{
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 1rem;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }}
        h1, h2 {{ margin-top: 0; font-weight: 600; }}
        .meta {{ color: var(--text-dim); font-size: 0.9rem; margin-bottom: 1rem; }}
        .tree-container {{ overflow-x: auto; }}
        details {{ margin-left: 1rem; border-left: 1px solid var(--border); }}
        summary {{
            list-style: none;
            cursor: pointer;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            display: flex;
            align-items: center;
            transition: background 0.2s;
            user-select: none;
        }}
        summary::-webkit-details-marker {{ display: none; }}
        summary:hover {{ background: rgba(99, 102, 241, 0.1); }}
        
        .node-content {{ display: flex; align-items: center; width: 100%; }}
        .toggle-icon {{ 
            width: 1.25rem; 
            font-size: 0.8rem; 
            color: var(--primary); 
            transition: transform 0.2s;
            display: inline-block;
            text-align: center;
            margin-right: 0.25rem;
        }}
        details[open] > summary .toggle-icon {{ transform: rotate(90deg); }}
        
        .icon {{ margin-right: 0.5rem; }}
        .node-name {{ flex-grow: 1; }}

        .depth-badge {{ 
            font-size: 0.7rem; 
            background: var(--primary); 
            padding: 2px 6px; 
            border-radius: 10px; 
            margin-left: 0.5rem;
            opacity: 0.8;
            white-space: nowrap;
        }}
        .size-badge {{
            font-size: 0.75rem;
            color: var(--secondary);
            font-family: 'JetBrains Mono', monospace;
            margin-left: 1rem;
            font-weight: 600;
            white-space: nowrap;
        }}
        .search-box {{
            width: 100%;
            padding: 0.75rem;
            border-radius: 0.5rem;
            border: 1px solid var(--border);
            background: rgba(15, 23, 42, 0.5);
            color: white;
            margin-bottom: 1rem;
            font-size: 1rem;
        }}
        .hidden {{ display: none; }}
        .top-path {{
            background: rgba(245, 158, 11, 0.1);
            border-left: 4px solid #f59e0b;
            padding: 0.5rem 1rem;
            margin-bottom: 0.5rem;
            border-radius: 4px;
        }}
        .controls {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
        }}
        .btn {{
            background: var(--primary);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            cursor: pointer;
            font-size: 0.85rem;
            transition: opacity 0.2s;
        }}
        .btn:hover {{ opacity: 0.9; }}
        .btn-secondary {{ background: var(--text-dim); }}
        code {{ font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: #a5b4fc; }}

        /* Tab Styles */
        .tabs {{
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.5rem;
        }}
        .tab-btn {{
            background: transparent;
            color: var(--text-dim);
            border: 1px solid transparent;
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
        }}
        .tab-btn:hover {{ color: var(--text); background: rgba(255,255,255,0.05); }}
        .tab-btn.active {{
            color: white;
            background: var(--primary);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
        }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; animation: fadeIn 0.3s ease-in-out; }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
    </style>
</head>
<body>
    <div class="glass">
        <h1>Анализ структуры папок</h1>
        <div class="meta">
            <strong>База:</strong> <code>{root}</code><br>
            <strong>Дата отчета:</strong> {timestamp}
        </div>
        
        <div class="tabs">
            <button class="tab-btn active" onclick="openTab('tab-deepest')">🔥 Самые глубокие пути</button>
            <button class="tab-btn" onclick="openTab('tab-tree')">📂 Дерево каталогов</button>
        </div>

        <div id="tab-deepest" class="tab-content active">
            <h2>Самые глубокие пути</h2>
            <div id="top-paths"></div>
        </div>

        <div id="tab-tree" class="tab-content">
            <h2>Дерево каталогов</h2>
            <input type="text" class="search-box" id="search" placeholder="Поиск папки в дереве...">
            <div class="controls">
                <button class="btn" onclick="expandAll()">Развернуть всё</button>
                <button class="btn btn-secondary" onclick="collapseAll()">Свернуть всё</button>
            </div>
            <div id="tree" class="tree-container"></div>
        </div>
    </div>

    <script>
        const treeData = {json_tree};
        const results = {json_results};

        function openTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.currentTarget.classList.add('active');
        }}

        function formatSize(bytes) {{
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }}

        function renderTopPaths() {{
            const container = document.getElementById('top-paths');
            results.forEach(res => {{
                const div = document.createElement('div');
                div.className = 'top-path';
                div.innerHTML = `<strong>#${{res.rank}}</strong> (Глубина: ${{res.depth}}, Размер: ${{formatSize(res.size)}}, Длина: ${{res.len}})<br><code>${{res.path}}</code>`;
                container.appendChild(div);
            }});
        }}

        function createNode(node) {{
            const hasChildren = node.c && node.c.length > 0;
            
            if (!hasChildren) {{
                const div = document.createElement('div');
                div.style.marginLeft = '2.25rem';
                div.style.padding = '0.25rem 0.5rem';
                div.className = 'node-leaf';
                div.innerHTML = `
                    <span class="icon">📁</span>
                    <span class="node-name" title="${{node.p}}">${{node.n}}</span>
                    <span class="depth-badge">d:${{node.d}}</span>
                    <span class="size-badge">${{formatSize(node.s)}}</span>
                `;
                div.style.display = 'flex';
                div.style.alignItems = 'center';
                return div;
            }}

            const details = document.createElement('details');
            const summary = document.createElement('summary');
            
            summary.innerHTML = `
                <span class="toggle-icon">▶</span>
                <span class="icon">📁</span>
                <span class="node-name" title="${{node.p}}">${{node.n}}</span>
                <span class="depth-badge">d:${{node.d}}</span>
                <span class="size-badge">${{formatSize(node.s)}}</span>
            `;
            
            details.appendChild(summary);
            node.c.forEach(child => {{
                details.appendChild(createNode(child));
            }});
            
            return details;
        }}

        function expandAll() {{
            document.querySelectorAll('details').forEach(d => d.open = true);
        }}

        function collapseAll() {{
            document.querySelectorAll('details').forEach(d => d.open = false);
        }}

        document.getElementById('search').addEventListener('input', (event) => {{
            const val = event.target.value.toLowerCase();
            const allNodes = document.querySelectorAll('details, .node-leaf');
            
            allNodes.forEach(node => {{
                const nameSpan = node.querySelector('.node-name');
                const name = nameSpan ? nameSpan.innerText.toLowerCase() : "";
                
                if (val === "" || name.includes(val)) {{
                    node.style.display = 'flex';
                    if (node.tagName === 'DETAILS') node.style.display = 'block';
                    
                    // Если нашли, раскрываем родителей
                    if (val !== "" && name.includes(val)) {{
                        let parent = node.parentElement;
                        while (parent && parent.tagName === 'DETAILS') {{
                            parent.open = true;
                            parent.style.display = 'block';
                            parent = parent.parentElement;
                        }}
                    }}
                }} else {{
                    node.style.display = 'none';
                }}
            }});
        }});

        renderTopPaths();
        document.getElementById('tree').appendChild(createNode(treeData));
    </script>
</body>
</html>"""
    return template


def find_deepest(
    root: str,
    top_k: int,
    by_length: bool,
    follow_symlinks: bool,
    max_depth: int,
) -> Tuple[List[Tuple[int, int, str, int]], Dict[str, Any]]:
    tree = scan_directory_tree(root, follow_symlinks, max_depth)
    nodes = flatten_tree(tree, os.path.abspath(root))
    scored: List[Tuple[int, int, str, int]] = []  # (depth, path_len, path, size)
    for n in nodes:
        scored.append((n["depth"], len(n["path"]), n["path"], n["size"]))

    if by_length:
        scored.sort(key=lambda t: (t[1], t[0], t[2]), reverse=True)
    else:
        scored.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)

    return scored[: max(1, top_k)], tree


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
        choices=["txt", "csv", "json", "html"],
        default="txt",
        help="Формат файла вывода: txt | csv | json | html (по умолчанию txt)",
    )
    parser.add_argument(
        "--tree-depth",
        type=int,
        default=10,
        help="Максимальная глубина дерева для HTML-отчета (по умолчанию 10)",
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

    results, tree = find_deepest(
        root=root,
        top_k=args.top,
        by_length=args.by_length,
        follow_symlinks=args.follow_symlinks,
        max_depth=args.tree_depth,
    )

    mode = "path length" if args.by_length else "depth"
    print(f"Base: {root}")
    print(f"Sort mode: {mode}")
    print()
    for rank, (depth, plen, path, size) in enumerate(results, start=1):
        print(f"#{rank}: depth={depth}, len={plen}, size={size}")
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
                writer.writerow(["rank", "depth", "path_length", "size_bytes", "path"]) 
                for rank, (depth, plen, path, size) in enumerate(results, start=1):
                    writer.writerow([rank, depth, plen, size, path])
        elif args.out_format == "json":
            json_payload = [
                {"rank": rank, "depth": depth, "path_length": plen, "size_bytes": size, "path": path}
                for rank, (depth, plen, path, size) in enumerate(results, start=1)
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
        else:  # html
            html_content = generate_html_report(root, tree, results)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        print(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()


