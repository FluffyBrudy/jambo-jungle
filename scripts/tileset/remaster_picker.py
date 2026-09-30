#!/usr/bin/env python3
"""
AI generated helper to help on color remaster using my custom API
which is private repo but url is public incase anyone wants to use
Interactive multi-select remaster picker (stdlib only, no subprocess).

Navigates the filesystem with a curses file browser, lets you toggle
multiple source images with SPACE, and auto-derives each target as
``<stem>_<theme_id><ext>`` in the same directory.

Examples:
    # interactive picker (theme + file browser UI)
    python3 scripts/tileset/remaster_picker.py

    # skip the theme screen
    python3 scripts/tileset/remaster_picker.py --theme blood_moon

    # skip the browser entirely (plain batch mode, no curses)
    python3 scripts/tileset/remaster_picker.py --theme blood_moon a.png b.png

    # preview what would happen without uploading
    python3 scripts/tileset/remaster_picker.py --theme blood_moon --dry-run

    # print equivalent `bun` commands instead of uploading from python
    python3 scripts/tileset/remaster_picker.py --theme blood_moon --emit-bun

Browser keys:
    up/down or j/k .... move cursor
    enter / right ...... enter directory
    left / backspace ... go up one directory
    space .............. select / unselect file under cursor (* multiple)
    a .................. select all images in current directory
    A .................. clear all selections
    f .................. toggle image-only filter
    c .................. confirm selection and start remaster
    q / esc ............ quit without doing anything

Target naming:
    <dir>/<stem>_<theme_id><ext>  e.g. jungle_bg_trees.png
    + blood_moon -> jungle_bg_trees_blood_moon.png
    (`--format jpeg` forces a `.jpg` extension.)
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid

PRESET_IDS = [
    "spring_blossom",
    "summer_lush",
    "autumn_harvest",
    "winter_frost",
    "forest_peak",
    "desert_scorched",
    "toxic_swamp",
    "abyssal_trench",
    "celestial_gold",
    "crystal_cavern",
    "dark_blight",
    "cyber_neon",
    "blood_moon",
]

THEME_KEYS = {
    "spring": "spring_blossom",
    "summer": "summer_lush",
    "autumn": "autumn_harvest",
    "fall": "autumn_harvest",
    "winter": "winter_frost",
}

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")

DEFAULT_API_BASE = "https://gametools-blush.vercel.app"
MAX_UPLOAD_BYTES = 8 * 1024 * 1024

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__ + "/../")))
# __file__ = scripts/tileset/remaster_picker.py -> root = scripts/../.. = repo
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_START_DIR = os.path.join(REPO_ROOT, "assets", "images")


# --------------------------------------------------------------------------- #
# pure helpers (os/path only -- no subprocess)                                 #
# --------------------------------------------------------------------------- #


def resolve_theme(raw: str) -> str:
    key = raw.strip().lower()
    if key in THEME_KEYS:
        return THEME_KEYS[key]
    if key in PRESET_IDS:
        return key
    raise ValueError(
        f'unknown theme "{raw}"\nvalid keys: {", ".join(sorted(THEME_KEYS))}\nvalid ids: {", ".join(PRESET_IDS)}'
    )


def api_base() -> str:
    return (os.environ.get("GAMETOOLS_API") or DEFAULT_API_BASE).rstrip("/")


def is_image(name: str) -> bool:
    return name.lower().endswith(IMAGE_EXTS)


def target_for(src: str, theme: str, fmt: str) -> str:
    """Same dir as src, stem + _<theme> + ext (jpeg forces .jpg)."""
    d = os.path.dirname(os.path.abspath(src))
    stem, ext = os.path.splitext(os.path.basename(src))
    if fmt == "jpeg":
        ext = ".jpg"
    elif not ext:
        ext = ".png"
    if stem.endswith(f"_{theme}"):
        return os.path.join(d, stem + ext)
    return os.path.join(d, f"{stem}_{theme}{ext}")


def bun_command(src: str, target: str, args: argparse.Namespace) -> str:
    parts = ["bun", "scripts/tileset/remaster.ts", "--theme", args.theme]
    if args.tile_size is not None:
        parts += ["--tile-size", str(args.tile_size)]
    if args.format != "png":
        parts += ["--format", args.format]
    if args.excluded:
        parts += ["--excluded", args.excluded]
    if args.selected:
        parts += ["--selected", args.selected]
    if args.force:
        parts += ["--force"]
    if args.api_base:
        parts += ["--api-base", args.api_base]
    parts += [src, target]
    return " ".join(parts)


# --------------------------------------------------------------------------- #
# upload (urllib only -- no subprocess, no third-party deps)                   #
# --------------------------------------------------------------------------- #


def _multipart(fields: dict[str, str], file_field: str, file_path: str) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    buf = bytearray()
    for k, v in fields.items():
        buf += f"--{boundary}\r\n".encode()
        buf += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
        buf += f"{v}\r\n".encode()
    filename = os.path.basename(file_path)
    ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    buf += f"--{boundary}\r\n".encode()
    buf += (f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n').encode()
    buf += f"Content-Type: {ctype}\r\n\r\n".encode()
    with open(file_path, "rb") as fh:
        buf += fh.read()
    buf += f"\r\n--{boundary}--\r\n".encode()
    return bytes(buf), boundary


def remaster_one(src: str, target: str, args: argparse.Namespace, base: str) -> tuple[str, str]:
    size = os.path.getsize(src)
    if size == 0:
        raise ValueError(f"source is empty: {src}")
    if size > MAX_UPLOAD_BYTES:
        raise ValueError(f"source is {size / 1048576:.1f} MB; API limit is 8 MB: {src}")
    if os.path.exists(target) and not args.force:
        raise FileExistsError(f"target exists, refusing to overwrite: {target}\npass --force to overwrite")

    fields: dict[str, str] = {"theme": args.theme, "format": args.format}
    if args.tile_size is not None:
        fields["tileSize"] = str(args.tile_size)
    if args.excluded:
        fields["excludedTileIndices"] = json.dumps(parse_int_list(args.excluded, "excluded"))
    if args.selected:
        fields["selectedTileIndices"] = json.dumps(parse_int_list(args.selected, "selected"))

    body, boundary = _multipart(fields, "image", src)
    req = urllib.request.Request(
        f"{base}/api/v1/tileset/remaster",
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
    )
    try:
        with urllib.request.urlopen(req) as res:
            data = res.read()
            theme = res.headers.get("x-remaster-theme", args.theme)
            dims = res.headers.get("x-remaster-dimensions", "?")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        try:
            parsed = json.loads(detail)
            if isinstance(parsed.get("detail"), str) and parsed["detail"]:
                detail = parsed["detail"]
        except (ValueError, AttributeError):
            pass
        raise RuntimeError(f"API error {e.code}: {detail or e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"cannot reach API at {base}: {e.reason}") from e

    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    with open(target, "wb") as fh:
        fh.write(data)
    return theme, dims


def parse_int_list(raw: str, flag: str) -> list[int]:
    nums: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            n = int(part)
        except ValueError:
            raise ValueError(f"--{flag} must be comma-separated non-negative ints")
        if n < 0:
            raise ValueError(f"--{flag} must be comma-separated non-negative ints")
        nums.append(n)
    if not nums:
        raise ValueError(f"--{flag} must be comma-separated non-negative ints")
    return nums


# --------------------------------------------------------------------------- #
# curses UI: theme screen + file browser (space = multi-select)                #
# --------------------------------------------------------------------------- #


def pick_theme_curses(stdscr) -> str | None:
    import curses

    idx = 0
    # pre-select via env hint if valid
    curses.curs_set(0)
    while True:
        stdscr.erase()
        stdscr.addstr(0, 0, "Select theme (up/down + enter, number shortcut, q quits):", curses.A_BOLD)
        for i, pid in enumerate(PRESET_IDS):
            marker = ">" if i == idx else " "
            attr = curses.A_REVERSE if i == idx else curses.A_NORMAL
            stdscr.addstr(i + 2, 0, f"{marker} [{i + 1:2d}] {pid}", attr)
        stdscr.addstr(len(PRESET_IDS) + 3, 0, "short keys also work: spring/summer/autumn(fall)/winter")
        stdscr.refresh()
        ch = stdscr.getch()
        if ch in (ord("q"), 27):
            return None
        elif ch in (curses.KEY_UP, ord("k")):
            idx = (idx - 1) % len(PRESET_IDS)
        elif ch in (curses.KEY_DOWN, ord("j")):
            idx = (idx + 1) % len(PRESET_IDS)
        elif ch in (curses.KEY_ENTER, 10, 13):
            return PRESET_IDS[idx]
        elif ord("1") <= ch <= ord("9"):
            n = ch - ord("1")
            if n < len(PRESET_IDS):
                return PRESET_IDS[n]


def browse_curses(stdscr, start_dir: str, theme: str) -> list[str]:
    """Curses file browser. SPACE toggles selection, 'c' confirms."""
    import curses

    cur = os.path.abspath(start_dir)
    cursor = 0
    top = 0
    selected: set[str] = set()
    images_only = False
    curses.curs_set(0)

    def entries() -> list[tuple[str, bool]]:
        try:
            names = sorted(os.listdir(cur), key=str.lower)
        except OSError as e:
            names = []
            stdscr.addstr(1, 0, f"cannot list {cur}: {e}")
        dirs = [n for n in names if os.path.isdir(os.path.join(cur, n)) and not n.startswith(".")]
        files = [n for n in names if os.path.isfile(os.path.join(cur, n))]
        if images_only:
            files = [n for n in files if is_image(n)]
        else:
            # hide dotfiles, keep everything else visible
            files = [n for n in files if not n.startswith(".")]
        return [("..", True)] + [(d, True) for d in dirs] + [(f, False) for f in files]

    while True:
        items = entries()
        cursor = max(0, min(cursor, len(items) - 1))
        h, w = stdscr.getmaxyx()
        per_page = max(1, h - 5)
        top = max(0, min(top, max(0, len(items) - per_page)))
        if cursor < top:
            top = cursor
        elif cursor >= top + per_page:
            top = cursor - per_page + 1

        stdscr.erase()
        stdscr.addstr(0, 0, f"dir: {cur}  [theme={theme}]  ({len(selected)} selected)", curses.A_BOLD)
        for row in range(per_page):
            i = top + row
            if i >= len(items):
                break
            name, is_dir = items[i]
            full = os.path.normpath(os.path.join(cur, name))
            mark = "[x]" if full in selected else "[ ]"
            attr = curses.A_REVERSE if i == cursor else curses.A_NORMAL
            label = (name + "/") if is_dir else f"{mark} {name}"
            if not is_dir:
                tgt = target_for(full, theme, "png")
                label = f"{mark} {name}  -> {os.path.basename(tgt)}"
            stdscr.addnstr(row + 1, 0, label, w - 1, attr)
        stdscr.addnstr(
            h - 1,
            0,
            "↑↓/jk move · enter/→ open · ←/bksp up · space select · a all-imgs · A clear · "
            "f filter · c confirm · q quit",
            w - 1,
            curses.A_DIM,
        )
        stdscr.refresh()
        ch = stdscr.getch()

        if ch in (ord("q"), 27):
            return []
        elif ch in (curses.KEY_UP, ord("k")):
            cursor -= 1
        elif ch in (curses.KEY_DOWN, ord("j")):
            cursor += 1
        elif ch in (curses.KEY_RIGHT, 10, 13):  # enter dir / confirm files? enter opens dirs only
            if not items:
                continue
            name, is_dir = items[cursor]
            full = os.path.normpath(os.path.join(cur, name))
            if is_dir:
                cur = full
                cursor, top = 0, 0
            else:
                # enter on a file toggles it too (convenient)
                if full in selected:
                    selected.discard(full)
                else:
                    selected.add(full)
                cursor += 1
        elif ch in (curses.KEY_LEFT, curses.KEY_BACKSPACE, 127, 8):
            parent = os.path.dirname(cur)
            if parent and parent != cur:
                cur = parent
                cursor, top = 0, 0
        elif ch == ord(" "):
            if items:
                name, is_dir = items[cursor]
                if not is_dir:
                    full = os.path.normpath(os.path.join(cur, name))
                    if full in selected:
                        selected.discard(full)
                    else:
                        selected.add(full)
                cursor += 1
        elif ch == ord("a"):
            for name, is_dir in items:
                if not is_dir and is_image(name):
                    selected.add(os.path.normpath(os.path.join(cur, name)))
        elif ch == ord("A"):
            selected.clear()
        elif ch == ord("f"):
            images_only = not images_only
            cursor, top = 0, 0
        elif ch == ord("c"):
            return sorted(selected)


def run_picker(start_dir: str, theme: str | None) -> tuple[str | None, list[str]]:
    """Returns (theme, sources). Empty sources = quit. Raises if no curses."""
    import curses

    result: dict[str, object] = {}

    def main(stdscr) -> None:
        t = theme or pick_theme_curses(stdscr)
        if t is None:
            result["theme"] = None
            result["sources"] = []
            return
        result["theme"] = t
        result["sources"] = browse_curses(stdscr, start_dir, t)

    curses.wrapper(main)
    return result.get("theme"), result.get("sources", [])  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# plain fallback picker (no curses): numbered list, space-separated picks      #
# --------------------------------------------------------------------------- #


def run_plain_picker(start_dir: str, theme: str) -> list[str]:
    cur = os.path.abspath(start_dir)
    selected: list[str] = []
    print(f"theme: {theme}")
    print("commands: <number> toggle · cd <dir|..> · ls · done · quit")
    while True:
        try:
            names = sorted(os.listdir(cur), key=str.lower)
        except OSError as e:
            print(f"cannot list {cur}: {e}")
            return []
        dirs = [n for n in names if os.path.isdir(os.path.join(cur, n))]
        files = [n for n in names if os.path.isfile(os.path.join(cur, n)) and not n.startswith(".")]
        print(f"\n[{cur}]")
        for i, d in enumerate(dirs):
            print(f"  d{i}: {d}/")
        for j, f in enumerate(files):
            full = os.path.normpath(os.path.join(cur, f))
            mark = "x" if full in selected else " "
            print(f"  {j}: [{mark}] {f} -> {os.path.basename(target_for(full, theme, 'png'))}")
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return []
        if raw in ("quit", "q"):
            return []
        if raw in ("done", "c", ""):
            return selected
        if raw == "ls":
            continue
        if raw.startswith("cd"):
            arg = raw[2:].strip()
            nxt = os.path.normpath(os.path.join(cur, arg)) if arg else cur
            if os.path.isdir(nxt):
                cur = nxt
            else:
                print(f"not a directory: {nxt}")
            continue
        # numbers like "1 3 5" or "d0" to cd
        ok = True
        for tok in raw.replace(",", " ").split():
            if tok.startswith("d") and tok[1:].isdigit() and int(tok[1:]) < len(dirs):
                cur = os.path.normpath(os.path.join(cur, dirs[int(tok[1:])]))
            elif tok.isdigit() and int(tok) < len(files):
                full = os.path.normpath(os.path.join(cur, files[int(tok)]))
                if full in selected:
                    selected.remove(full)
                else:
                    selected.append(full)
            else:
                # bare filename?
                full = os.path.normpath(os.path.join(cur, tok))
                if os.path.isfile(full):
                    if full in selected:
                        selected.remove(full)
                    else:
                        selected.append(full)
                else:
                    print(f"unknown: {tok}")
                    ok = False
        if ok and raw:
            print(f"selected ({len(selected)}): " + ", ".join(selected))


# --------------------------------------------------------------------------- #
# main                                                                        #
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Pick multiple images via file browser; remaster each to <stem>_<theme>.<ext>.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("sources", nargs="*", help="source image(s); omit to launch the browser")
    p.add_argument("--theme", default=None, help="theme key or preset id (omit = picker screen)")
    p.add_argument("--tile-size", dest="tile_size", type=int, default=None)
    p.add_argument("--format", choices=["png", "jpeg"], default="png")
    p.add_argument("--excluded", default=None, help="comma-separated locked tile indices")
    p.add_argument("--selected", default=None, help="comma-separated indices; only these remaster")
    p.add_argument("--force", action="store_true", help="allow overwriting existing targets")
    p.add_argument("--api-base", default=None)
    p.add_argument("--start-dir", default=None, help="browser start directory")
    p.add_argument("--no-curses", action="store_true", help="use plain line-based picker")
    p.add_argument("--dry-run", action="store_true", help="print src -> target, do not upload")
    p.add_argument("--emit-bun", action="store_true", help="print bun remaster.ts commands, do not upload")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        theme = resolve_theme(args.theme) if args.theme else None
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if args.tile_size is not None and not (2 <= args.tile_size <= 64):
        print("error: --tile-size must be an int between 2 and 64", file=sys.stderr)
        return 2
    if args.theme:
        args.theme = theme  # normalize short keys (spring -> spring_blossom)

    start_dir = args.start_dir or (DEFAULT_START_DIR if os.path.isdir(DEFAULT_START_DIR) else REPO_ROOT)

    sources = list(args.sources)
    if not sources:
        if args.no_curses:
            if theme is None:
                print(f"pick a theme: {', '.join(PRESET_IDS)}")
                try:
                    raw = input("theme> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    return 1
                try:
                    theme = resolve_theme(raw)
                except ValueError as e:
                    print(f"error: {e}", file=sys.stderr)
                    return 2
                args.theme = theme
            sources = run_plain_picker(start_dir, theme)
        else:
            try:
                picked_theme, sources = run_picker(start_dir, theme)
            except Exception as e:
                print(
                    f"curses UI unavailable ({e}); retry with --no-curses",
                    file=sys.stderr,
                )
                return 1
            if picked_theme is None or not sources:
                print("cancelled.")
                return 0
            theme = picked_theme
            args.theme = theme
    else:
        if theme is None:
            print("error: --theme is required when passing source files directly", file=sys.stderr)
            return 2
        # validate sources exist (os only)
        missing = [s for s in sources if not os.path.isfile(s)]
        if missing:
            for m in missing:
                print(f"error: source not found: {m}", file=sys.stderr)
            return 3

    assert args.theme, "theme must be resolved by now"
    base = (args.api_base or api_base()).rstrip("/")
    failures = 0
    for src in sources:
        src_abs = os.path.abspath(src)
        target = target_for(src_abs, args.theme, args.format)
        if args.dry_run or args.emit_bun:
            if args.emit_bun:
                print(bun_command(src_abs, target, args))
            else:
                exists = " [exists, use --force]" if os.path.exists(target) and not args.force else ""
                print(f"{src_abs} -> {target}{exists}")
            continue
        try:
            t, dims = remaster_one(src_abs, target, args, base)
            kb = os.path.getsize(target) / 1024
            print(f"ok: {target}\n    {dims}, theme {t}, {kb:.1f} KB")
        except FileExistsError as e:
            print(f"error: {e}", file=sys.stderr)
            failures += 1
        except (ValueError, RuntimeError) as e:
            print(f"error ({src}): {e}", file=sys.stderr)
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
