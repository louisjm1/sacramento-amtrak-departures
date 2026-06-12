"""Scheduled Sacramento departures from the 511 GTFS static feed.

The Amtrak realtime feed only carries trains that are currently tracked, so the
board looks sparse hours ahead. This module reads the full published timetable
(511 operator "AM" = Capitol Corridor) and yields every scheduled SAC departure
in the window; the caller overlays realtime delays on top.

Pure stdlib. The GTFS zip is cached on disk and refreshed about daily — 511's
gateway is slow and rate-limited (60 req/hr), so we fetch it rarely.
"""

from __future__ import annotations

import csv
import os
import re
import time
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# GTFS sources. "url": None means fetch from 511's datafeeds by operator id;
# a string is a direct zip URL (San Joaquins isn't on 511, so it uses the
# SJJPA/Gold Runner CloudFront feed).
OPERATORS = {
    "AM": {"route": "Capitol Corridor", "url": None},
    "GR": {"route": "San Joaquins",
           "url": "https://d34tiw64n5z4oh.cloudfront.net/wp-content/uploads/GRGTFS.zip"},
}
RAIL_ROUTE_TYPE = "2"  # GTFS route_type 2 = rail; exclude Thruway buses (type 3)

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gtfs_cache")
PACIFIC = ZoneInfo("America/Los_Angeles")
DATAFEED = "https://api.511.org/transit/datafeeds?api_key={tok}&operator_id={op}"
MAX_AGE_H = 18      # refresh the cached zip at most this often
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday"]


def _token() -> str:
    """511 API token: env var, else reuse the transit-map project's .env."""
    tok = os.environ.get("TRANSIT_511_TOKEN")
    if tok:
        return tok
    envp = os.path.expanduser("~/dev/bay-area-transit-map/.env")
    if os.path.exists(envp):
        with open(envp) as f:
            for line in f:
                if line.startswith("TRANSIT_511_TOKEN="):
                    return line.split("=", 1)[1].strip()
    raise RuntimeError("Set TRANSIT_511_TOKEN (511.org API token)")


def has_token() -> bool:
    """True if a 511 token is configured (non-raising; used to decide whether
    to prompt the user for one)."""
    try:
        return bool(_token())
    except Exception:  # noqa: BLE001
        return False


def ensure_zip(operator: str = "AM") -> str:
    """Return path to a fresh-enough cached GTFS zip, downloading if needed."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{operator}.zip")
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < MAX_AGE_H * 3600:
        return path
    url = OPERATORS[operator]["url"] or DATAFEED.format(tok=_token(), op=operator)
    last = None
    for _ in range(6):  # 511's gateway 504s often; retry with backoff
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "sac-board/1.0"})
            data = urllib.request.urlopen(req, timeout=90).read()
            with open(path, "wb") as f:
                f.write(data)
            return path
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(8)
    if os.path.exists(path):
        return path  # stale cache beats nothing
    raise RuntimeError(f"could not fetch 511 {operator} GTFS: {last}")


def _rows(z: zipfile.ZipFile, name: str) -> list[dict]:
    return list(csv.DictReader(z.read(name).decode("utf-8-sig").splitlines()))


def _service_index(z: zipfile.ZipFile):
    """Return active(date) -> set of service_ids running that calendar date."""
    base = {c["service_id"]: c for c in _rows(z, "calendar.txt")}
    add, rem = defaultdict(set), defaultdict(set)
    for e in _rows(z, "calendar_dates.txt"):
        (add if e["exception_type"] == "1" else rem)[e["date"]].add(e["service_id"])

    def active(date) -> set:
        ds = date.strftime("%Y%m%d")
        out = {sid for sid, c in base.items()
               if c["start_date"] <= ds <= c["end_date"]
               and c[WEEKDAYS[date.weekday()]] == "1"}
        out |= add.get(ds, set())
        out -= rem.get(ds, set())
        return out

    return active


def _gtfs_secs(t: str) -> int:
    """GTFS HH:MM:SS (hours may exceed 24) -> seconds past service midnight."""
    h, m, s = (int(x) for x in t.split(":"))
    return h * 3600 + m * 60 + s


def _clean_dest(headsign: str) -> str:
    low = headsign.lower()
    for key, city in (("oakland", "Oakland"), ("san jose", "San Jose"),
                      ("emeryville", "Emeryville"), ("auburn", "Auburn"),
                      ("roseville", "Roseville"), ("salesforce", "San Francisco"),
                      ("san francisco", "San Francisco"), ("bakersfield", "Bakersfield"),
                      ("stockton", "Stockton"), ("fresno", "Fresno"),
                      ("merced", "Merced"), ("sacramento", "Sacramento")):
        if key in low:
            return city
    return headsign.split("-")[0].strip()


def scheduled_departures(now: datetime, hours: int, operator: str = "AM",
                         past_grace: timedelta = timedelta(0)):
    """List of (train_num:int, route:str, dest:str, sched:datetime) for SAC
    departures within [now - past_grace, now + hours]. SAC arrivals/terminations
    are excluded. `past_grace` lets the caller also see recently-passed scheduled
    times so it can keep trains that are running late (their revised time hasn't
    come yet); the caller filters those by the live delay.
    """
    z = zipfile.ZipFile(ensure_zip(operator))
    route = OPERATORS[operator]["route"]
    trips = {t["trip_id"]: t for t in _rows(z, "trips.txt")}
    rail_routes = {r["route_id"] for r in _rows(z, "routes.txt")
                   if r["route_type"] == RAIL_ROUTE_TYPE}
    sac_ids = {r["stop_id"] for r in _rows(z, "stops.txt")
               if r["stop_name"].strip().lower() == "sacramento"}

    # One pass over stop_times: track each trip's last sequence and its SAC stop.
    last_seq: dict[str, int] = defaultdict(int)
    sac_stops: list[tuple] = []  # (trip_id, seq, departure_time, pickup_type)
    for r in _rows(z, "stop_times.txt"):
        seq = int(r["stop_sequence"])
        if seq > last_seq[r["trip_id"]]:
            last_seq[r["trip_id"]] = seq
        if r["stop_id"] in sac_ids:
            sac_stops.append((r["trip_id"], seq, r["departure_time"],
                              r.get("pickup_type", "0")))

    active = _service_index(z)
    horizon = now + timedelta(hours=hours)
    earliest = now - past_grace
    local_now = now.astimezone(PACIFIC)
    out = []
    # A <=24h window touches at most yesterday..tomorrow once after-midnight
    # GTFS times (e.g. 25:40) are accounted for.
    for offset in (-1, 0, 1):
        date = (local_now + timedelta(days=offset)).date()
        running = active(date)
        midnight = datetime(date.year, date.month, date.day, tzinfo=PACIFIC)
        for trip_id, seq, dep_time, pickup in sac_stops:
            trip = trips[trip_id]
            if trip["route_id"] not in rail_routes:
                continue  # Thruway bus, not a train
            if trip["service_id"] not in running:
                continue
            if seq >= last_seq[trip_id]:
                continue  # SAC is the final stop -> arrival, not a departure
            if pickup == "1" or not dep_time:
                continue  # drop-off only / no departure
            sched = midnight + timedelta(seconds=_gtfs_secs(dep_time))
            if sched < earliest or sched > horizon:
                continue
            num = int(re.sub(r"\D", "", trip_id) or 0)
            out.append((num, route, _clean_dest(trip.get("trip_headsign", "")), sched))
    return out


if __name__ == "__main__":
    from datetime import timezone
    now = datetime.now(timezone.utc)
    rows = []
    for op in OPERATORS:
        rows += scheduled_departures(now, 24, op)
    for num, route, dest, sched in sorted(rows, key=lambda r: r[3]):
        print(f"{sched.astimezone():%m/%d %H:%M}  #{num:<5} {route:<18} to {dest}")
