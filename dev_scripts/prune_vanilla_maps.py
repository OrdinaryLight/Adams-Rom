#!/usr/bin/env python3
"""Keep the maps named in config/map_prune.json and remove the rest.

Run this from the project root. Start with --plan, then use --apply after
reviewing the report. The command stores a recoverable backup outside the
repository before it removes any map or layout directory.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAP_INCLUDE = re.compile(r'^\s*\.include "data/maps/([^/]+)/scripts\.inc"\s*$', re.MULTILINE)
SCRIPT_INCLUDE = re.compile(r'^\s*\.include "(data/scripts/[^"]+\.inc)"\s*$')
LABEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):{1,2}(?!:)", re.MULTILINE)
TOKEN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
MAP_TOKEN = re.compile(r"\bMAP_[A-Z0-9_]+\b")
TEXT_LABEL = re.compile(r"^(gText_|.*_Text_)")

# These labels are reached through a script call. A return command keeps the
# caller alive. All other removed scripts end safely after unlocking controls.
RETURN_LABELS = {
    "BattleFrontier_BattlePike_EventScript_CloseCurtain",
    "MossdeepCity_SpaceCenter_2F_EventScript_ChoosePartyForMultiBattle",
    "Ferry_EventScript_DepartIslandSouth",
    "Ferry_EventScript_DepartIslandWest",
}
LINK_STANDBY_LABEL = "gText_LinkStandby3"


@dataclass(frozen=True)
class MapRecord:
    name: str
    map_id: str
    layout_id: str
    directory: Path
    map_json: Path


@dataclass(frozen=True)
class Plan:
    keep_maps: tuple[MapRecord, ...]
    delete_maps: tuple[MapRecord, ...]
    keep_layout_ids: frozenset[str]
    delete_layout_dirs: tuple[Path, ...]
    compatibility_labels: tuple[str, ...]
    unknown_maps: tuple[str, ...]


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def write_json(path: Path, value: Any) -> None:
    text = json.dumps(value, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def load_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / "config" / "map_prune.json"
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != 1:
        raise ValueError("config/map_prune.json must use schema_version 1")
    if not manifest.get("keep_maps"):
        raise ValueError("config/map_prune.json must keep at least one map")
    return manifest


def inventory_maps(root: Path) -> dict[str, MapRecord]:
    maps: dict[str, MapRecord] = {}
    for directory in sorted((root / "data" / "maps").iterdir()):
        map_json = directory / "map.json"
        if not directory.is_dir() or not map_json.exists():
            continue
        data = read_json(map_json)
        maps[directory.name] = MapRecord(
            directory.name,
            data["id"],
            data["layout"],
            directory,
            map_json,
        )
    return maps


def required_vanilla_ids(root: Path) -> set[str]:
    data = read_json(root / "tools" / "mapjson" / "required_map_defines.json")
    return {entry[0] for entry in data["required_maps"]}


def registered_map_names(root: Path) -> set[str]:
    groups = read_json(root / "data" / "maps" / "map_groups.json")
    return {
        name
        for group in groups["group_order"]
        for name in groups.get(group, [])
    }


def validate_kept_maps(root: Path, records: dict[str, MapRecord], manifest: dict[str, Any]) -> None:
    registered = registered_map_names(root)
    for name in manifest["keep_maps"]:
        if name not in records:
            raise ValueError(f"Kept map is missing: {name}")
        if name not in registered:
            raise ValueError(f"Kept map is not registered in map_groups.json: {name}")

    entrypoint = manifest["entrypoint"]
    entry_record = next(
        (record for record in records.values() if record.map_id == entrypoint["map_id"]),
        None,
    )
    if entry_record is None or entry_record.name not in manifest["keep_maps"]:
        raise ValueError("The entrypoint map must be in keep_maps")


def validate_map_references(records: tuple[MapRecord, ...]) -> None:
    kept_ids = {record.map_id for record in records}
    for record in records:
        data = read_json(record.map_json)
        for connection in data.get("connections") or []:
            target = connection.get("map")
            if target and target not in kept_ids:
                raise ValueError(f"{record.name} has a connection to deleted map {target}")
        for warp in data.get("warp_events") or []:
            target = warp.get("dest_map")
            if target and target not in {"MAP_DYNAMIC", "MAP_UNDEFINED"} and target not in kept_ids:
                raise ValueError(f"{record.name} has a warp to deleted map {target}")
        for key in ("shared_events_map", "shared_scripts_map"):
            target = data.get(key)
            if target and target not in kept_ids:
                raise ValueError(f"{record.name} shares {key} with deleted map {target}")


def layout_records(root: Path) -> dict[str, dict[str, Any]]:
    layouts = read_json(root / "data" / "layouts" / "layouts.json")
    return {layout["id"]: layout for layout in layouts["layouts"]}


def collect_external_labels(root: Path, deleted_maps: tuple[MapRecord, ...], keep_maps: tuple[MapRecord, ...]) -> tuple[dict[str, str], set[str]]:
    definitions: dict[str, str] = {}
    for record in deleted_maps:
        script = record.directory / "scripts.inc"
        if not script.exists():
            continue
        text = script.read_text(encoding="utf-8")
        for label in LABEL.findall(text):
            definitions.setdefault(label, text)

    source_files: list[Path] = []
    for directory in (root / "src", root / "include", root / "data"):
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix not in {".c", ".h", ".s", ".inc", ".pory"}:
                continue
            if "data/maps" in path.as_posix():
                continue
            if path.name == "removed_map_compat.inc":
                continue
            source_files.append(path)
    for record in keep_maps:
        source_files.extend(record.directory.rglob("*.inc"))
        source_files.extend(record.directory.rglob("*.pory"))

    tokens: set[str] = set()
    surviving_definitions: set[str] = set()
    for path in source_files:
        source = path.read_text(encoding="utf-8")
        tokens.update(TOKEN.findall(source))
        surviving_definitions.update(LABEL.findall(source))
    return definitions, set(definitions).intersection(tokens).difference(surviving_definitions)


def regenerate_compatibility_from_backup(root: Path, backup: Path, link_log: Path) -> int:
    """Rebuild shims from a pre-prune backup without restoring deleted maps."""
    definitions: dict[str, str] = {}
    scripts = list((backup / "data" / "maps").glob("*/scripts.inc"))
    scripts.extend((root / "data" / "scripts").glob("*.inc"))
    for script in scripts:
        text = script.read_text(encoding="utf-8")
        for label in LABEL.findall(text):
            definitions.setdefault(label, text)
    compatibility = root / "data" / "scripts" / "removed_map_compat.inc"
    labels = set(LABEL.findall(compatibility.read_text(encoding="utf-8")))
    labels.difference_update({"RemovedMap_EmptyText", "RemovedMap_Return", "RemovedMap_EndScript"})
    missing = set(re.findall(r"undefined reference to [`']([A-Za-z_][A-Za-z0-9_]*)'", link_log.read_text(encoding="utf-8")))
    unsupported = missing.difference(definitions)
    if unsupported:
        raise ValueError("Missing labels have no script definition: " + ", ".join(sorted(unsupported)))
    labels.update(missing)
    compatibility.write_text(render_compatibility_include(definitions, tuple(sorted(labels))), encoding="utf-8")
    return len(labels)


def extract_string_lines(script_text: str, label: str) -> list[str]:
    lines = script_text.splitlines()
    for index, line in enumerate(lines):
        if line in {f"{label}:", f"{label}::"}:
            result: list[str] = []
            for candidate in lines[index + 1:]:
                if LABEL.match(candidate):
                    break
                if candidate.lstrip().startswith(".string"):
                    result.append(candidate)
                elif result and candidate.strip():
                    break
            return result
    return []


def render_compatibility_include(definitions: dict[str, str], labels: tuple[str, ...]) -> str:
    text_labels = [label for label in labels if TEXT_LABEL.match(label) and label != LINK_STANDBY_LABEL]
    return_labels = [label for label in labels if label in RETURN_LABELS]
    script_labels = [label for label in labels if label not in set(text_labels) | set(return_labels) | {LINK_STANDBY_LABEL}]
    lines = ["@ Generated by tools/prune_vanilla_maps.py. Do not edit.", "", "\t.align 2"]

    if LINK_STANDBY_LABEL in labels:
        lines.append("")
        lines.append(f"{LINK_STANDBY_LABEL}::")
        original = extract_string_lines(definitions[LINK_STANDBY_LABEL], LINK_STANDBY_LABEL)
        lines.extend(original or ['\t.string "Link standby.$"'])

    if text_labels:
        lines.append("")
        lines.extend(f"{label}::" for label in text_labels)
        lines.append("RemovedMap_EmptyText::")
        lines.append('\t.string "$"')

    if return_labels:
        lines.append("")
        lines.extend(f"{label}::" for label in return_labels)
        lines.append("RemovedMap_Return::")
        lines.append("\treturn")

    if script_labels:
        lines.append("")
        lines.extend(f"{label}::" for label in script_labels)
        lines.append("RemovedMap_EndScript::")
        lines.append("\treleaseall")
        lines.append("\tend")

    return "\n".join(lines) + "\n"


def build_plan(root: Path, manifest: dict[str, Any]) -> Plan:
    records = inventory_maps(root)
    validate_kept_maps(root, records, manifest)
    keep_maps = tuple(records[name] for name in manifest["keep_maps"])
    validate_map_references(keep_maps)
    vanilla_ids = required_vanilla_ids(root)
    extra_vanilla = set(manifest.get("legacy_unregistered_vanilla_maps", []))
    unknown_maps = tuple(
        sorted(
            record.name
            for record in records.values()
            if record.name not in manifest["keep_maps"]
            and record.map_id not in vanilla_ids
            and record.name not in extra_vanilla
        )
    )
    delete_maps = tuple(record for name, record in sorted(records.items()) if name not in manifest["keep_maps"])
    layouts = layout_records(root)
    keep_layout_ids = frozenset(record.layout_id for record in keep_maps)
    missing_layouts = keep_layout_ids.difference(layouts)
    if missing_layouts:
        raise ValueError(f"Kept map layout is missing: {', '.join(sorted(missing_layouts))}")
    keep_layout_dirs = {
        (root / layout["border_filepath"]).parent.resolve()
        for layout_id, layout in layouts.items()
        if layout_id in keep_layout_ids
    }
    delete_layout_dirs = tuple(
        directory
        for directory in sorted((root / "data" / "layouts").iterdir())
        if directory.is_dir() and directory.resolve() not in keep_layout_dirs
    )
    definitions, labels = collect_external_labels(root, delete_maps, keep_maps)
    return Plan(
        keep_maps,
        delete_maps,
        keep_layout_ids,
        delete_layout_dirs,
        tuple(sorted(labels)),
        unknown_maps,
    )


def report(plan: Plan) -> str:
    lines = [
        f"Keep maps: {len(plan.keep_maps)}",
        f"Delete map directories: {len(plan.delete_maps)}",
        f"Keep layouts: {len(plan.keep_layout_ids)}",
        f"Delete layout directories: {len(plan.delete_layout_dirs)}",
        f"Compatibility labels: {len(plan.compatibility_labels)}",
    ]
    if plan.unknown_maps:
        lines.append("Unknown map directories that block apply: " + ", ".join(plan.unknown_maps))
    return "\n".join(lines)


def rewrite_map_groups(root: Path, plan: Plan) -> None:
    original = read_json(root / "data" / "maps" / "map_groups.json")
    keep_names = {record.name for record in plan.keep_maps}
    groups: dict[str, Any] = {"group_order": []}
    for group in original["group_order"]:
        names = [name for name in original.get(group, []) if name in keep_names]
        if names:
            groups["group_order"].append(group)
            groups[group] = names
    write_json(root / "data" / "maps" / "map_groups.json", groups)


def rewrite_layouts(root: Path, plan: Plan) -> None:
    original = read_json(root / "data" / "layouts" / "layouts.json")
    original["layouts"] = [layout for layout in original["layouts"] if layout["id"] in plan.keep_layout_ids]
    write_json(root / "data" / "layouts" / "layouts.json", original)


def rewrite_event_script_includes(root: Path, plan: Plan) -> None:
    keep_names = {record.name for record in plan.keep_maps}
    path = root / "data" / "event_scripts.s"
    lines = path.read_text(encoding="utf-8").splitlines()
    kept: list[str] = []
    inserted = False
    for line in lines:
        match = MAP_INCLUDE.match(line)
        if match:
            if match.group(1) in keep_names:
                kept.append(line)
            continue
        script_match = SCRIPT_INCLUDE.match(line)
        if script_match:
            script_path = root / script_match.group(1)
            if script_path.exists() and MAP_TOKEN.search(script_path.read_text(encoding="utf-8")):
                continue
        if line.strip() == '.include "data/scripts/removed_map_compat.inc"':
            if not inserted:
                kept.append(line)
                inserted = True
            continue
        kept.append(line)
    if not inserted:
        kept.append('\t.include "data/scripts/removed_map_compat.inc"')
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")


def rewrite_wild_encounters(root: Path, plan: Plan, manifest: dict[str, Any]) -> None:
    path = root / "src" / "data" / "wild_encounters.json"
    data = read_json(path)
    keep_ids = {record.map_id for record in plan.keep_maps}
    seed = manifest.get("wild_encounter_seed")
    for group in data["wild_encounter_groups"]:
        if group.get("for_maps"):
            existing = list(group["encounters"])
            kept = [entry for entry in existing if entry.get("map") in keep_ids]
            if seed and seed["map"] in keep_ids and not any(entry.get("map") == seed["map"] for entry in kept):
                source = next((entry for entry in existing if entry.get("map") == seed["source_map"]), None)
                if source is None:
                    raise ValueError(f"Wild encounter source is missing: {seed['source_map']}")
                custom = copy.deepcopy(source)
                custom["map"] = seed["map"]
                custom["base_label"] = seed["base_label"]
                kept.append(custom)
            group["encounters"] = kept
        else:
            group["encounters"] = []
    write_json(path, data)


def make_backup(root: Path, plan: Plan) -> Path:
    backup_root = root.parent / f"{root.name}-map-prune-backups"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = backup_root / timestamp
    backup.mkdir(parents=True, exist_ok=False)
    for path in [
        root / "data" / "maps" / "map_groups.json",
        root / "data" / "layouts" / "layouts.json",
        root / "data" / "event_scripts.s",
        root / "src" / "data" / "wild_encounters.json",
        root / "data" / "scripts" / "removed_map_compat.inc",
    ]:
        if path.exists():
            target = backup / path.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    for directory in [record.directory for record in plan.delete_maps] + list(plan.delete_layout_dirs):
        target = backup / directory.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(directory, target)
    (backup / "README.txt").write_text(
        "This backup was created by tools/prune_vanilla_maps.py before physical map deletion.\n",
        encoding="utf-8",
    )
    return backup


def apply(root: Path, plan: Plan, manifest: dict[str, Any]) -> Path:
    if plan.unknown_maps:
        raise ValueError("Refusing to delete unknown map directories: " + ", ".join(plan.unknown_maps))
    backup = make_backup(root, plan)
    compatibility = root / "data" / "scripts" / "removed_map_compat.inc"
    if plan.delete_maps:
        definitions, labels = collect_external_labels(root, plan.delete_maps, plan.keep_maps)
        compatibility.parent.mkdir(parents=True, exist_ok=True)
        compatibility.write_text(render_compatibility_include(definitions, tuple(sorted(labels))), encoding="utf-8")
    elif not compatibility.exists():
        compatibility.parent.mkdir(parents=True, exist_ok=True)
        compatibility.write_text(render_compatibility_include({}, ()), encoding="utf-8")
    rewrite_map_groups(root, plan)
    rewrite_layouts(root, plan)
    rewrite_event_script_includes(root, plan)
    rewrite_wild_encounters(root, plan, manifest)
    for record in plan.delete_maps:
        if record.directory.exists():
            shutil.rmtree(record.directory)
    for directory in plan.delete_layout_dirs:
        if directory.exists():
            shutil.rmtree(directory)
    return backup


def verify(root: Path, manifest: dict[str, Any]) -> None:
    plan = build_plan(root, manifest)
    if plan.unknown_maps:
        raise ValueError("Unknown map directories remain: " + ", ".join(plan.unknown_maps))
    if len(plan.keep_maps) != len(inventory_maps(root)):
        raise ValueError("Vanilla map directories remain")
    groups = read_json(root / "data" / "maps" / "map_groups.json")
    if set(groups["group_order"]) != {"gMapGroup_TownsAndRoutes"}:
        raise ValueError("The map registry does not contain only the custom map group")
    includes = (root / "data" / "event_scripts.s").read_text(encoding="utf-8")
    map_includes = MAP_INCLUDE.findall(includes)
    if map_includes != list(manifest["keep_maps"]):
        raise ValueError("data/event_scripts.s does not contain only kept map scripts")
    print("Map-prune source checks passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "apply", "verify", "regenerate-compat"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--link-log", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if not (root / "Makefile").exists():
        raise ValueError(f"Not a pokeemerald project: {root}")
    manifest = load_manifest(root)
    if args.command == "regenerate-compat":
        if args.backup is None or args.link_log is None:
            raise ValueError("regenerate-compat requires --backup and --link-log")
        label_count = regenerate_compatibility_from_backup(root, args.backup.resolve(), args.link_log.resolve())
        print(f"Regenerated compatibility labels: {label_count}")
        return 0
    if args.command == "verify":
        verify(root, manifest)
        return 0
    plan = build_plan(root, manifest)
    print(report(plan))
    if args.command == "apply":
        backup = apply(root, plan, manifest)
        print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
