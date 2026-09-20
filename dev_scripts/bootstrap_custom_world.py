#!/usr/bin/env python3
"""Register AdamsRomStartingArea as the Emerald new-game map."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else Path.cwd()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Expected source text was not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    if not (ROOT / "Makefile").exists():
        raise RuntimeError(f"Not a project root: {ROOT}")

    layout_path = ROOT / "data/layouts/layouts.json"
    layouts = read_json(layout_path)
    if not any(layout["id"] == "LAYOUT_ADAMS_ROM_STARTING_AREA" for layout in layouts["layouts"]):
        layouts["layouts"].append({
            "id": "LAYOUT_ADAMS_ROM_STARTING_AREA",
            "name": "AdamsRomStartingArea_Layout",
            "width": 20,
            "height": 60,
            "primary_tileset": "gTileset_General",
            "secondary_tileset": "gTileset_Petalburg",
            "border_filepath": "data/layouts/AdamsRomStartingArea/border.bin",
            "blockdata_filepath": "data/layouts/AdamsRomStartingArea/map.bin",
        })
        write_json(layout_path, layouts)

    groups_path = ROOT / "data/maps/map_groups.json"
    groups = read_json(groups_path)
    group = groups["gMapGroup_TownsAndRoutes"]
    if "AdamsRomStartingArea" not in group:
        group.append("AdamsRomStartingArea")
        write_json(groups_path, groups)

    heal_path = ROOT / "src/data/heal_locations.json"
    heals = read_json(heal_path)
    if not any(item["id"] == "HEAL_LOCATION_ADAMS_ROM_STARTING_AREA" for item in heals["heal_locations"]):
        heals["heal_locations"].append({
            "id": "HEAL_LOCATION_ADAMS_ROM_STARTING_AREA",
            "map": "MAP_ADAMS_ROM_STARTING_AREA",
            "x": 10,
            "y": 57,
        })
        write_json(heal_path, heals)

    event_scripts = ROOT / "data/event_scripts.s"
    include = '\t.include "data/maps/AdamsRomStartingArea/scripts.inc"\n'
    if include not in event_scripts.read_text(encoding="utf-8"):
        with event_scripts.open("a", encoding="utf-8") as output:
            output.write("\n" + include)

    replace_once(
        ROOT / "src/new_game.c",
        """        SetWarpDestination(MAP_GROUP(MAP_INSIDE_OF_TRUCK), MAP_NUM(MAP_INSIDE_OF_TRUCK), WARP_ID_NONE, -1, -1);""",
        """        SetWarpDestination(
            MAP_GROUP(MAP_ADAMS_ROM_STARTING_AREA),
            MAP_NUM(MAP_ADAMS_ROM_STARTING_AREA),
            WARP_ID_NONE,
            10,
            57
        );""",
    )
    replace_once(
        ROOT / "src/overworld.c",
        """    if (IS_FRLG)
        gFieldCallback = FieldCB_WarpExitFadeFromBlack;
    else
        gFieldCallback = ExecuteTruckSequence;""",
        """    gFieldCallback = FieldCB_WarpExitFadeFromBlack;""",
    )


if __name__ == "__main__":
    main()
