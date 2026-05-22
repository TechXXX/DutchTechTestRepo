# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import posixpath
import re
import ssl
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import xbmc  # type: ignore
    import xbmcaddon  # type: ignore
    import xbmcgui  # type: ignore
    import xbmcvfs  # type: ignore
except ImportError:  # Allows local syntax/unit checks outside Kodi.
    xbmc = None
    xbmcaddon = None
    xbmcgui = None
    xbmcvfs = None


ADDON_ID = "script.kodiskin.widget.importer"
ADDON_NAME = "KodiSkin Widget Importer"
SHORTCUTS_DATA = "special://profile/addon_data/script.skinshortcuts/"
ADDON_DATA = "special://profile/addon_data/{}/".format(ADDON_ID)
INCLUDE_NAME = "script-skinshortcuts-includes.xml"
USER_AGENT = "{}/0.1.0 Kodi".format(ADDON_ID)
PCLOUD_API_DEFAULT = "https://api.pcloud.com"
PCLOUD_API_EU = "https://eapi.pcloud.com"


class ImportCancelled(Exception):
    pass


class ImportErrorWithMessage(Exception):
    pass


@dataclass(frozen=True)
class ImportFile:
    source_path: Path
    source_skin: str
    target_name: str
    kind: str


@dataclass(frozen=True)
class ShortcutPackage:
    source_skin: str
    files: List[ImportFile]
    include_path: Optional[Path]
    skipped_hashes: List[Path]


class KodiUI:
    def __init__(self) -> None:
        self.dialog = xbmcgui.Dialog() if xbmcgui else None

    def log(self, message: str, level: Optional[int] = None) -> None:
        line = "[{}] {}".format(ADDON_ID, message)
        if xbmc:
            xbmc.log(line, level if level is not None else xbmc.LOGINFO)
        else:
            print(line)

    def ok(self, heading: str, *lines: str) -> None:
        message = "\n".join([line for line in lines if line])
        if self.dialog:
            try:
                self.dialog.ok(heading, message)
            except TypeError:
                self.dialog.ok(heading, *lines[:3])
        else:
            print("{}\n{}".format(heading, message))

    def error(self, *lines: str) -> None:
        self.ok(ADDON_NAME, *lines)

    def yesno(self, heading: str, *lines: str) -> bool:
        message = "\n".join([line for line in lines if line])
        if self.dialog:
            try:
                return bool(self.dialog.yesno(heading, message))
            except TypeError:
                return bool(self.dialog.yesno(heading, *lines[:3]))
        print("{}\n{}".format(heading, message))
        return True

    def select(self, heading: str, options: Sequence[str]) -> int:
        if self.dialog:
            return int(self.dialog.select(heading, list(options)))
        return 0

    def input(self, heading: str, default: str = "") -> str:
        if self.dialog:
            input_type = getattr(xbmcgui, "INPUT_ALPHANUM", 0)
            return self.dialog.input(heading, defaultt=default, type=input_type)
        return default

    def browse_zip(self) -> str:
        if not self.dialog:
            return ""
        try:
            return self.dialog.browseSingle(
                1,
                "Choose widget backup ZIP",
                "files",
                ".zip",
                False,
                False,
                "",
            )
        except TypeError:
            return self.dialog.browse(1, "Choose widget backup ZIP", "files", ".zip")

    def progress(self, heading: str, message: str):
        if not xbmcgui:
            return None
        progress = xbmcgui.DialogProgress()
        progress.create(heading, message)
        return progress


def main() -> None:
    ui = KodiUI()
    work_dir: Optional[Path] = None
    try:
        source = choose_source(ui)
        if not source:
            return

        target_skin = get_current_skin()
        if not target_skin:
            raise ImportErrorWithMessage("Could not detect the active Kodi skin.")

        work_dir = make_work_dir()
        package_root = prepare_source(source, work_dir, ui)
        package = discover_package(package_root, target_skin, ui)

        if not package.files:
            raise ImportErrorWithMessage(
                "No Skin Shortcuts DATA/properties files were found in that ZIP."
            )

        if not confirm_import(package, target_skin, ui):
            return

        backup_dir = import_shortcuts(package.files, target_skin, ui)
        save_last_source(source)

        include_note = ""
        if package.include_path and ui.yesno(
            ADDON_NAME,
            "The ZIP also contains a generated include.",
            "Copy it to the active skin too?",
            "Choose No if you want Skin Shortcuts to rebuild it.",
        ):
            include_backup = import_generated_include(package.include_path, ui)
            include_note = "Generated include backup: {}".format(include_backup)

        ui.ok(
            ADDON_NAME,
            "Imported {} Skin Shortcuts files.".format(len(package.files)),
            "Backup: {}".format(backup_dir),
            include_note or "Reload the skin or restart Kodi so widgets rebuild.",
        )
    except ImportCancelled:
        ui.log("Import cancelled")
    except Exception as exc:
        ui.log("Import failed: {}".format(exc), getattr(xbmc, "LOGERROR", None) if xbmc else None)
        ui.error("Import failed.", str(exc))
    finally:
        if work_dir is not None:
            shutil.rmtree(str(work_dir), ignore_errors=True)


def choose_source(ui: KodiUI) -> str:
    last_source = load_last_source()
    options: List[str] = []
    if last_source:
        options.append("Use last source")
    options.extend(["Paste URL or path", "Browse for ZIP"])

    choice = ui.select(ADDON_NAME, options)
    if choice < 0:
        raise ImportCancelled()

    label = options[choice]
    if label == "Use last source":
        return last_source
    if label == "Browse for ZIP":
        return strip_quotes(ui.browse_zip())
    return strip_quotes(ui.input("Paste widget ZIP, pCloud link, or path", last_source))


def confirm_import(package: ShortcutPackage, target_skin: str, ui: KodiUI) -> bool:
    data_count = len([item for item in package.files if item.kind == "data"])
    prop_count = len([item for item in package.files if item.kind == "properties"])
    return ui.yesno(
        ADDON_NAME,
        "Source skin: {}".format(package.source_skin),
        "Target skin: {}".format(target_skin),
        "Import {} DATA and {} properties file(s)?".format(data_count, prop_count),
    )


def get_current_skin() -> str:
    if xbmc:
        return xbmc.getSkinDir()
    return "skin.arctic.horizon.2.patched"


def make_work_dir() -> Path:
    root = translate_path(vfs_join(ADDON_DATA, "work"))
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = root / stamp
    path.mkdir(parents=True, exist_ok=True)
    return path


def prepare_source(source: str, work_dir: Path, ui: KodiUI) -> Path:
    if not source:
        raise ImportCancelled()

    if is_pcloud_public_link(source):
        ui.log("Resolving pCloud public link")
        source = resolve_pcloud_download_url(source)

    parsed = urllib.parse.urlparse(source)
    if parsed.scheme in ("http", "https"):
        zip_path = work_dir / "source.zip"
        download_url(source, zip_path, ui)
        return extract_or_fail(zip_path, work_dir / "extracted")

    if is_directory_source(source):
        return Path(translate_path(source))

    zip_path = work_dir / "source.zip"
    copy_source_to_local(source, zip_path)
    return extract_or_fail(zip_path, work_dir / "extracted")


def extract_or_fail(zip_path: Path, extract_dir: Path) -> Path:
    if not zipfile.is_zipfile(str(zip_path)):
        raise ImportErrorWithMessage(describe_non_zip(zip_path))
    safe_extract_zip(zip_path, extract_dir)
    return extract_dir


def discover_package(root: Path, target_skin: str, ui: KodiUI) -> ShortcutPackage:
    package = discover_package_once(root, target_skin, ui)
    if package.files:
        return package

    nested_zips = [path for path in root.rglob("*.zip") if path.is_file()]
    if len(nested_zips) == 1:
        nested_root = root.parent / "nested-zip"
        ui.log("No shortcuts found; extracting nested ZIP {}".format(nested_zips[0].name))
        safe_extract_zip(nested_zips[0], nested_root)
        return discover_package_once(nested_root, target_skin, ui)

    return package


def discover_package_once(root: Path, target_skin: str, ui: KodiUI) -> ShortcutPackage:
    candidates: List[ImportFile] = []
    include_paths: List[Path] = []
    skipped_hashes: List[Path] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part == "__MACOSX" for part in path.parts):
            continue

        name = path.name
        if name == INCLUDE_NAME:
            include_paths.append(path)
            continue

        if name.endswith(".hash"):
            source_skin = name[:-5]
            if source_skin:
                skipped_hashes.append(path)
            continue

        if name.endswith(".properties"):
            source_skin = name[: -len(".properties")]
            if looks_like_skin_id(source_skin):
                candidates.append(
                    ImportFile(path, source_skin, "{}.properties".format(target_skin), "properties")
                )
            continue

        data_name = parse_data_filename(name)
        if data_name:
            source_skin, menu_name = data_name
            candidates.append(
                ImportFile(
                    path,
                    source_skin,
                    "{}-{}.DATA.xml".format(target_skin, menu_name),
                    "data",
                )
            )

    if not candidates:
        return ShortcutPackage("", [], first_path(include_paths), skipped_hashes)

    source_skin = choose_source_skin(candidates, ui)
    chosen = [item for item in candidates if item.source_skin == source_skin]
    deduped = dedupe_by_target_name(chosen, root)

    return ShortcutPackage(source_skin, deduped, first_path(include_paths), skipped_hashes)


def choose_source_skin(candidates: Sequence[ImportFile], ui: KodiUI) -> str:
    skins = sorted(set(item.source_skin for item in candidates if item.source_skin))
    if not skins:
        raise ImportErrorWithMessage("Could not detect the source skin id in the backup.")
    if len(skins) == 1:
        return skins[0]

    labels = [
        "{} ({} files)".format(skin, len([item for item in candidates if item.source_skin == skin]))
        for skin in skins
    ]
    choice = ui.select("Choose source skin", labels)
    if choice < 0:
        raise ImportCancelled()
    return skins[choice]


def dedupe_by_target_name(candidates: Sequence[ImportFile], root: Path) -> List[ImportFile]:
    by_name: Dict[str, ImportFile] = {}
    for item in candidates:
        current = by_name.get(item.target_name)
        if current is None or candidate_score(item.source_path, root) > candidate_score(
            current.source_path, root
        ):
            by_name[item.target_name] = item
    return [by_name[name] for name in sorted(by_name)]


def candidate_score(path: Path, root: Path) -> Tuple[int, int]:
    rel = relative_parts(path, root)
    normalized = "/".join(part.lower() for part in rel)
    in_addon_data = "addon_data/script.skinshortcuts" in normalized
    shallow = -len(rel)
    return (2 if in_addon_data else 1, shallow)


def import_shortcuts(files: Sequence[ImportFile], target_skin: str, ui: KodiUI) -> str:
    ensure_vfs_dir(SHORTCUTS_DATA)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup_dir = vfs_join(ADDON_DATA, "backups", stamp, "script.skinshortcuts")
    ensure_vfs_dir(backup_dir)

    target_hash_name = "{}.hash".format(target_skin)
    targets = [item.target_name for item in files] + [target_hash_name]
    for target_name in targets:
        dest = vfs_join(SHORTCUTS_DATA, target_name)
        if vfs_exists(dest):
            backup_dest = vfs_join(backup_dir, target_name)
            copy_vfs(dest, backup_dest)

    for item in files:
        dest = vfs_join(SHORTCUTS_DATA, item.target_name)
        if vfs_exists(dest):
            delete_vfs(dest)
        copy_vfs(str(item.source_path), dest)
        ui.log("Imported {}".format(item.target_name))

    hash_path = vfs_join(SHORTCUTS_DATA, target_hash_name)
    if vfs_exists(hash_path):
        delete_vfs(hash_path)
        ui.log("Removed {} to force Skin Shortcuts rebuild".format(target_hash_name))

    return backup_dir


def import_generated_include(include_path: Path, ui: KodiUI) -> str:
    skin_include_dir = "special://skin/1080i/"
    target = vfs_join(skin_include_dir, INCLUDE_NAME)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup_dir = vfs_join(ADDON_DATA, "backups", stamp, "generated-include")
    ensure_vfs_dir(backup_dir)

    if vfs_exists(target):
        copy_vfs(target, vfs_join(backup_dir, INCLUDE_NAME))
        delete_vfs(target)
    copy_vfs(str(include_path), target)
    ui.log("Copied generated include to active skin")
    return backup_dir


def resolve_pcloud_download_url(public_link: str) -> str:
    code = extract_pcloud_code(public_link)
    if not code:
        raise ImportErrorWithMessage("That pCloud link does not contain a public code.")

    errors: List[str] = []
    for api_base in pcloud_api_bases(public_link):
        try:
            metadata_response = fetch_pcloud_json(api_base, "showpublink", {"code": code})
        except Exception as exc:
            errors.append("{}: {}".format(api_base, exc))
            continue

        if metadata_response.get("result") != 0:
            errors.append(pcloud_error(metadata_response))
            continue

        metadata = metadata_response.get("metadata") or {}
        name = str(metadata.get("name") or "")
        is_folder = bool(metadata.get("isfolder"))
        if is_folder:
            return build_pcloud_api_url(api_base, "getpubzip", {"code": code, "filename": "skinshortcuts.zip"})

        if name.lower().endswith(".zip"):
            download_response = fetch_pcloud_json(
                api_base, "getpublinkdownload", {"code": code, "forcedownload": "1"}
            )
            if download_response.get("result") == 0:
                hosts = download_response.get("hosts") or []
                path = download_response.get("path")
                if hosts and path:
                    return "https://{}{}".format(str(hosts[0]), str(path))
            errors.append(pcloud_error(download_response))

        return build_pcloud_api_url(api_base, "getpubzip", {"code": code, "filename": "skinshortcuts.zip"})

    raise ImportErrorWithMessage("Could not resolve pCloud link: {}".format("; ".join(errors)))


def fetch_pcloud_json(api_base: str, method: str, params: Dict[str, str]) -> Dict[str, object]:
    url = build_pcloud_api_url(api_base, method, params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with open_url(request, timeout=30) as response:
        payload = response.read().decode("utf-8", "replace")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ImportErrorWithMessage("Unexpected response from pCloud.")
    return data


def build_pcloud_api_url(api_base: str, method: str, params: Dict[str, str]) -> str:
    return "{}/{}?{}".format(api_base.rstrip("/"), method, urllib.parse.urlencode(params))


def pcloud_api_bases(public_link: str) -> List[str]:
    host = urllib.parse.urlparse(public_link).netloc.lower()
    if host.startswith("e.") or host.startswith("e1.") or host.startswith("e2."):
        return [PCLOUD_API_EU, PCLOUD_API_DEFAULT]
    return [PCLOUD_API_DEFAULT, PCLOUD_API_EU]


def pcloud_error(response: Dict[str, object]) -> str:
    error = response.get("error") or "unknown pCloud error"
    result = response.get("result")
    return "{} ({})".format(error, result) if result is not None else str(error)


def download_url(url: str, dest: Path, ui: KodiUI) -> None:
    progress = ui.progress(ADDON_NAME, "Downloading widget backup...")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with open_url(request, timeout=60) as response:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            with open(str(dest), "wb") as handle:
                while True:
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    downloaded += len(chunk)
                    if progress:
                        if progress.iscanceled():
                            raise ImportCancelled()
                        percent = int(downloaded * 100 / total) if total else 0
                        progress.update(min(percent, 100), "Downloading widget backup...")
    finally:
        if progress:
            progress.close()


def safe_extract_zip(zip_path: Path, extract_dir: Path) -> None:
    extract_dir.mkdir(parents=True, exist_ok=True)
    root = extract_dir.resolve()
    with zipfile.ZipFile(str(zip_path)) as archive:
        for member in archive.infolist():
            target = (extract_dir / member.filename).resolve()
            if not is_inside(target, root):
                raise ImportErrorWithMessage("Unsafe path in ZIP: {}".format(member.filename))
            archive.extract(member, str(extract_dir))


def parse_data_filename(name: str) -> Optional[Tuple[str, str]]:
    suffix = ".DATA.xml"
    if not name.endswith(suffix) or "-" not in name:
        return None
    base = name[: -len(suffix)]
    source_skin, menu_name = base.split("-", 1)
    if not looks_like_skin_id(source_skin) or not menu_name:
        return None
    return source_skin, menu_name


def looks_like_skin_id(value: str) -> bool:
    return bool(re.match(r"^skin\.[A-Za-z0-9_.-]+$", value))


def is_pcloud_public_link(source: str) -> bool:
    parsed = urllib.parse.urlparse(source)
    host = parsed.netloc.lower()
    return ("pcloud.link" in host or "pcloud.com" in host) and bool(extract_pcloud_code(source))


def extract_pcloud_code(public_link: str) -> str:
    parsed = urllib.parse.urlparse(public_link)
    query = urllib.parse.parse_qs(parsed.query)
    if query.get("code"):
        return query["code"][0]

    fragment = parsed.fragment
    if fragment:
        fragment_query = urllib.parse.parse_qs(fragment.lstrip("#"))
        if fragment_query.get("code"):
            return fragment_query["code"][0]

    match = re.search(r"(?:^|[?&#])code=([^&#]+)", public_link)
    return urllib.parse.unquote(match.group(1)) if match else ""


def open_url(request: urllib.request.Request, timeout: int):
    try:
        return urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.URLError as exc:
        if is_ssl_verification_error(exc):
            context = ssl._create_unverified_context()
            return urllib.request.urlopen(request, timeout=timeout, context=context)
        raise


def is_ssl_verification_error(exc: urllib.error.URLError) -> bool:
    reason = getattr(exc, "reason", None)
    return isinstance(reason, ssl.SSLError) and "CERTIFICATE_VERIFY_FAILED" in str(reason)


def is_directory_source(source: str) -> bool:
    if xbmcvfs and source.startswith(("special://", "smb://", "nfs://")):
        try:
            return bool(xbmcvfs.isdir(source))
        except Exception:
            return False
    path = Path(translate_path(source))
    return path.is_dir()


def copy_source_to_local(source: str, dest: Path) -> None:
    if xbmcvfs and source.startswith(("special://", "smb://", "nfs://", "ftp://")):
        if not xbmcvfs.copy(source, str(dest)):
            raise ImportErrorWithMessage("Could not copy source ZIP from {}".format(source))
        return

    local = Path(translate_path(source))
    if not local.exists():
        raise ImportErrorWithMessage("Source path does not exist: {}".format(source))
    shutil.copy2(str(local), str(dest))


def describe_non_zip(path: Path) -> str:
    try:
        text = path.read_bytes()[:2048].decode("utf-8", "replace").strip()
        data = json.loads(text)
        if isinstance(data, dict) and data.get("error"):
            return "Downloaded pCloud response was not a ZIP: {}".format(pcloud_error(data))
        if text:
            return "Downloaded file is not a ZIP. First response text: {}".format(text[:300])
    except Exception:
        pass
    return "Downloaded file is not a ZIP archive."


def strip_quotes(value: str) -> str:
    value = (value or "").strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def translate_path(path: str) -> Path:
    if xbmcvfs:
        translated = xbmcvfs.translatePath(path)
        if isinstance(translated, bytes):
            translated = translated.decode("utf-8")
        return Path(translated)
    if path.startswith("special://profile/"):
        return Path.cwd() / "_kodi_profile" / path[len("special://profile/") :]
    if path.startswith("special://skin/"):
        return Path.cwd() / "_kodi_skin" / path[len("special://skin/") :]
    return Path(path)


def vfs_join(base: str, *parts: str) -> str:
    base = base.rstrip("/")
    clean_parts = [str(part).strip("/") for part in parts if str(part).strip("/")]
    return "/".join([base] + clean_parts)


def ensure_vfs_dir(path: str) -> None:
    if xbmcvfs:
        xbmcvfs.mkdirs(path)
    else:
        translate_path(path).mkdir(parents=True, exist_ok=True)


def vfs_exists(path: str) -> bool:
    if xbmcvfs:
        return bool(xbmcvfs.exists(path))
    return translate_path(path).exists()


def copy_vfs(source: str, dest: str) -> None:
    parent = posixpath.dirname(dest)
    if parent:
        ensure_vfs_dir(parent)

    if xbmcvfs:
        if not xbmcvfs.copy(source, dest):
            raise ImportErrorWithMessage("Could not copy {} to {}".format(source, dest))
        return

    source_path = translate_path(source)
    dest_path = translate_path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(source_path), str(dest_path))


def delete_vfs(path: str) -> None:
    if xbmcvfs:
        xbmcvfs.delete(path)
    else:
        target = translate_path(path)
        if target.exists():
            target.unlink()


def load_last_source() -> str:
    path = translate_path(vfs_join(ADDON_DATA, "last-source.txt"))
    try:
        return path.read_text("utf-8").strip()
    except Exception:
        return ""


def save_last_source(source: str) -> None:
    path = translate_path(vfs_join(ADDON_DATA, "last-source.txt"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, "utf-8")


def first_path(paths: Sequence[Path]) -> Optional[Path]:
    return paths[0] if paths else None


def relative_parts(path: Path, root: Path) -> Tuple[str, ...]:
    try:
        return path.relative_to(root).parts
    except ValueError:
        return path.parts


def is_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
