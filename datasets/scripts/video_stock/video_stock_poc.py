#!/usr/bin/env python3
"""Mini PoC for stock-video discovery aimed at temporal pipeline evaluation."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_QUERIES = [
    "construction worker",
    "hard hat worker",
    "safety vest construction",
    "construction site people",
]
PEXELS_LICENSE_URL = "https://www.pexels.com/license/"
PIXABAY_LICENSE_URL = "https://pixabay.com/service/license-summary/"


@dataclass
class Candidate:
    source: str
    source_id: str
    query: str
    source_url: str
    author: str
    author_url: str
    duration_s: int | None
    width: int | None
    height: int | None
    fps: float | None
    preview_url: str
    video_url: str
    video_width: int | None
    video_height: int | None
    video_quality: str
    license_name: str
    license_url: str
    local_video_path: str = ""
    local_contact_sheet_path: str = ""
    decision: str = "pending"
    notes: str = ""

    def as_row(self) -> dict[str, Any]:
        return self.__dict__.copy()


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key.removeprefix("export ").strip()
        value = value.strip().strip('\"').strip("'")
        os.environ.setdefault(key, value)


def request_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def download_file(url: str, dest: Path, *, retries: int = 2) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return True
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "e-ovrt-video-stock-poc/0.1"})
            with urllib.request.urlopen(request, timeout=90) as response, dest.open("wb") as fh:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    fh.write(chunk)
            return True
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt >= retries:
                print(f"warn: download failed: {url} ({exc})", file=sys.stderr)
                return False
            time.sleep(2)
    return False


def choose_pexels_file(video_files: list[dict[str, Any]]) -> dict[str, Any] | None:
    mp4s = [item for item in video_files if item.get("file_type") == "video/mp4" and item.get("link")]
    if not mp4s:
        return None
    return sorted(
        mp4s,
        key=lambda item: (
            0 if item.get("quality") == "sd" else 1,
            int(item.get("width") or 99999) * int(item.get("height") or 99999),
        ),
    )[0]


def choose_pixabay_file(videos: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    for quality in ["tiny", "small", "medium", "large"]:
        item = videos.get(quality)
        if isinstance(item, dict) and item.get("url"):
            return quality, item
    return None


def pexels_search(query: str, per_query: int, min_duration: int, max_duration: int) -> list[Candidate]:
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        print("warn: PEXELS_API_KEY not configured; skipping Pexels", file=sys.stderr)
        return []

    params = {
        "query": query,
        "per_page": str(per_query),
        "orientation": "landscape",
        "size": "small",
        "locale": "en-US",
    }
    url = "https://api.pexels.com/v1/videos/search?" + urllib.parse.urlencode(params)
    try:
        data = request_json(url, headers={"Authorization": key})
    except urllib.error.HTTPError as exc:
        print(f"warn: Pexels query failed for {query!r}: HTTP {exc.code}", file=sys.stderr)
        return []
    except urllib.error.URLError as exc:
        print(f"warn: Pexels query failed for {query!r}: {exc}", file=sys.stderr)
        return []
    candidates = []
    for video in data.get("videos", []):
        duration = video.get("duration")
        if duration is not None and not (min_duration <= int(duration) <= max_duration):
            continue
        selected = choose_pexels_file(video.get("video_files", []))
        if not selected:
            continue
        user = video.get("user") or {}
        candidates.append(
            Candidate(
                source="pexels",
                source_id=str(video.get("id", "")),
                query=query,
                source_url=video.get("url", ""),
                author=user.get("name", ""),
                author_url=user.get("url", ""),
                duration_s=duration,
                width=video.get("width"),
                height=video.get("height"),
                fps=selected.get("fps"),
                preview_url=video.get("image", ""),
                video_url=selected.get("link", ""),
                video_width=selected.get("width"),
                video_height=selected.get("height"),
                video_quality=selected.get("quality", ""),
                license_name="Pexels License",
                license_url=PEXELS_LICENSE_URL,
            )
        )
    return candidates


def pixabay_search(query: str, per_query: int, min_duration: int, max_duration: int) -> list[Candidate]:
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        print("warn: PIXABAY_API_KEY not configured; skipping Pixabay", file=sys.stderr)
        return []

    params = {
        "key": key,
        "q": query,
        "per_page": str(per_query),
        "video_type": "film",
        "safesearch": "true",
        "orientation": "horizontal",
    }
    url = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode(params)
    try:
        data = request_json(url)
    except urllib.error.HTTPError as exc:
        print(f"warn: Pixabay query failed for {query!r}: HTTP {exc.code}", file=sys.stderr)
        return []
    except urllib.error.URLError as exc:
        print(f"warn: Pixabay query failed for {query!r}: {exc}", file=sys.stderr)
        return []
    candidates = []
    for video in data.get("hits", []):
        duration = video.get("duration")
        if duration is not None and not (min_duration <= int(duration) <= max_duration):
            continue
        selected = choose_pixabay_file(video.get("videos", {}))
        if not selected:
            continue
        quality, file_data = selected
        candidates.append(
            Candidate(
                source="pixabay",
                source_id=str(video.get("id", "")),
                query=query,
                source_url=video.get("pageURL", ""),
                author=video.get("user", ""),
                author_url=f"https://pixabay.com/users/{video.get('user', '')}-{video.get('user_id', '')}/",
                duration_s=duration,
                width=file_data.get("width") or video.get("pictureWidth"),
                height=file_data.get("height") or video.get("pictureHeight"),
                fps=None,
                preview_url=video.get("picture_id", ""),
                video_url=file_data.get("url", ""),
                video_width=file_data.get("width"),
                video_height=file_data.get("height"),
                video_quality=quality,
                license_name="Pixabay Content License",
                license_url=PIXABAY_LICENSE_URL,
            )
        )
    return candidates


def make_contact_sheet(video_path: Path, output_path: Path, frames: int) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = 4
    rows = max(1, (frames + columns - 1) // columns)
    vf = f"fps=1,scale=240:-1,tile={columns}x{rows}:padding=8:margin=8"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        vf,
        "-frames:v",
        "1",
        str(output_path),
    ]
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
        return True

    fallback = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        "thumbnail,scale=480:-1",
        "-frames:v",
        "1",
        str(output_path),
    ]
    result = subprocess.run(fallback, cwd=ROOT, check=False)
    return result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0


def write_outputs(candidates: list[Candidate], out_dir: Path) -> None:
    reports = out_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    jsonl_path = reports / "candidates.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for candidate in candidates:
            fh.write(json.dumps(candidate.as_row(), ensure_ascii=False) + "\n")

    csv_path = reports / "candidates.csv"
    fieldnames = list(Candidate.__dataclass_fields__.keys())
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for candidate in candidates:
            writer.writerow(candidate.as_row())

    review_path = reports / "review_manifest.csv"
    review_fields = [
        "decision",
        "source",
        "source_id",
        "query",
        "duration_s",
        "source_url",
        "local_contact_sheet_path",
        "expected_condition",
        "worker_visible",
        "helmet_state",
        "vest_state",
        "notes",
    ]
    with review_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=review_fields)
        writer.writeheader()
        for candidate in candidates:
            writer.writerow(
                {
                    "decision": "pending",
                    "source": candidate.source,
                    "source_id": candidate.source_id,
                    "query": candidate.query,
                    "duration_s": candidate.duration_s,
                    "source_url": candidate.source_url,
                    "local_contact_sheet_path": candidate.local_contact_sheet_path,
                    "expected_condition": "",
                    "worker_visible": "",
                    "helmet_state": "",
                    "vest_state": "",
                    "notes": "",
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", nargs="*", default=DEFAULT_QUERIES)
    parser.add_argument("--sources", default="pexels,pixabay")
    parser.add_argument("--per-query", type=int, default=4)
    parser.add_argument("--max-candidates", type=int, default=16)
    parser.add_argument("--min-duration", type=int, default=4)
    parser.add_argument("--max-duration", type=int, default=25)
    parser.add_argument("--contact-frames", type=int, default=8)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "datasets" / "interim" / "video_stock_poc",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.out_dir.is_absolute():
        args.out_dir = ROOT / args.out_dir
    load_dotenv(ROOT / ".env")
    sources = {source.strip() for source in args.sources.split(",") if source.strip()}
    candidates: list[Candidate] = []
    seen: set[tuple[str, str]] = set()

    for query in args.queries:
        batch: list[Candidate] = []
        if "pexels" in sources:
            batch.extend(pexels_search(query, args.per_query, args.min_duration, args.max_duration))
        if "pixabay" in sources:
            batch.extend(pixabay_search(query, args.per_query, args.min_duration, args.max_duration))

        for candidate in batch:
            key = (candidate.source, candidate.source_id)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(candidate)
            if len(candidates) >= args.max_candidates:
                break
        if len(candidates) >= args.max_candidates:
            break

    videos_dir = args.out_dir / "videos"
    sheets_dir = args.out_dir / "contact_sheets"
    for idx, candidate in enumerate(candidates, start=1):
        stem = f"{idx:03d}_{candidate.source}_{candidate.source_id}"
        video_path = videos_dir / f"{stem}.mp4"
        sheet_path = sheets_dir / f"{stem}.jpg"
        if download_file(candidate.video_url, video_path):
            candidate.local_video_path = video_path.relative_to(ROOT).as_posix()
            if make_contact_sheet(video_path, sheet_path, args.contact_frames):
                candidate.local_contact_sheet_path = sheet_path.relative_to(ROOT).as_posix()

    write_outputs(candidates, args.out_dir)
    print(f"candidates: {len(candidates)}")
    print(f"out_dir: {args.out_dir.relative_to(ROOT)}")
    print(f"review_manifest: {(args.out_dir / 'reports' / 'review_manifest.csv').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
