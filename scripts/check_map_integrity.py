#!/usr/bin/env python3
"""Map integrity checker: verify editor-produced maps are self-consistent.

Invariants enforced (per painted tile on every tile layer):
  1. ttype is a valid index into resources.tilesets
  2. variant < tilesets[ttype].tile_count
  3. stored gid == tilesets[ttype].firstgid + variant   (the corruption
     signature observed when the editor removes/reorders tilesets)

Optional --collision cross-check reports which in-map gids lack collision
entries and vice versa (informational only; exit code unaffected).

Usage:
    python scripts/check_map_integrity.py data/maps/0.json \
        [--collision data/collision/tileset.collision.json]

Exit codes: 0 = clean, 1 = violations found, 2 = usage/load error.

Eventually this finding helped me to identify the bug that was silently hiding in the shadow
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("map", type=Path)
    ap.add_argument("--collision", type=Path, default=None)
    args = ap.parse_args()

    pygame.init()
    pygame.display.set_mode((64, 64))

    from tilemap_parser import load_map, load_tileset_collision

    try:
        map_data = load_map(args.map)
    except Exception as e:  # noqa: BLE001
        print(f"LOAD ERROR: {e}")
        return 2

    tss = map_data.parsed.tilesets
    firstgids = [ts.firstgid for ts in tss]
    counts = [ts.tile_count for ts in tss]
    names = [Path(ts.path).name for ts in tss]

    print(f"map      : {args.map}")
    print(f"tilesets : {len(tss)}")
    print(f"layers   : {len(map_data.parsed.layers)}")

    errors: list[str] = []
    warnings: list[str] = []
    total = 0
    per_ttype: dict[int, int] = {}

    for layer in map_data.parsed.layers:
        if layer.layer_type != "tile":
            continue
        for pos, tile in layer.tiles.items():
            total += 1
            per_ttype[tile.ttype] = per_ttype.get(tile.ttype, 0) + 1

            if not isinstance(tile.ttype, int) or not 0 <= tile.ttype < len(tss):
                errors.append(f"{layer.name} {pos}: ttype {tile.ttype!r} outside 0..{len(tss) - 1}")
                continue
            if tile.variant >= counts[tile.ttype]:
                errors.append(
                    f"{layer.name} {pos}: variant {tile.variant} >= "
                    f"tile_count {counts[tile.ttype]} of '{names[tile.ttype]}'"
                )
            expected = firstgids[tile.ttype] + tile.variant
            if tile.gid is not None and tile.gid != expected:
                errors.append(
                    f"{layer.name} {pos}: gid {tile.gid} != "
                    f"firstgid[{tile.ttype}]({firstgids[tile.ttype]}) + "
                    f"variant({tile.variant}) = {expected}"
                )

    print(f"tiles    : {total}  per-tileset {dict(sorted(per_ttype.items()))}")

    if args.collision:
        col = load_tileset_collision(args.collision)
        if col is None:
            print(f"COLLISION: file not found: {args.collision}")
        else:
            gids_in_map: set[int] = set()
            for layer in map_data.parsed.layers:
                if layer.layer_type != "tile":
                    continue
                for tile in layer.tiles.values():
                    t = tile.ttype
                    if isinstance(t, int) and 0 <= t < len(tss):
                        gids_in_map.add(firstgids[t] + tile.variant)
            missing = sorted(g for g in gids_in_map if not col.has_collision(g))
            extra = sorted(k for k in col.tiles if k not in set(gids_in_map))
            print(
                f"collision: {len(col.tiles)} entries | map gids without "
                f"collision entry: {len(missing)} (ok: interiors) | unused "
                f"entries: {len(extra)}"
            )

    if warnings:
        for w in warnings:
            print(f"WARN  {w}")
    if errors:
        print(f"\nFAIL: {len(errors)} violation(s)")
        for e in errors[:20]:
            print(f"  - {e}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")
        return 1

    print("\nOK: map is self-consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
