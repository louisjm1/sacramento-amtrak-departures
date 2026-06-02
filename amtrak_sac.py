"""Pull real-time Amtrak data for Sacramento (SAC) and build a station board.

Data source: Amtraker v3 (https://api-v3.amtraker.com), a community service that
decrypts Amtrak's own "Track a Train" map feed. No API key. Be polite: poll no
faster than ~once a minute.

Pure stdlib so it runs anywhere (incl. a Raspberry Pi with a bare Python).
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import gtfs_sched

STATION = "SAC"
MAX_HOURS = 24  # only show departures within this many hours from now
TRAINS_URL = "https://api-v3.amtraker.com/v3/trains"
USER_AGENT = "sac-eink-board/1.0 (personal display)"
TIMEOUT = 15

# Amtrak destName values are full station names ("Oakland-Jack London Square").
# A departure board shows the city, so map the common SAC-route endpoints.
DEST_CITY = {
    "EMY": "Emeryville", "CHI": "Chicago", "LAX": "Los Angeles",
    "SEA": "Seattle", "SAC": "Sacramento", "OKJ": "Oakland",
    "SJC": "San Jose", "BFD": "Bakersfield", "ARN": "Auburn",
    "RSV": "Roseville", "MTZ": "Martinez", "STK": "Stockton",
    "RIC": "Richmond", "FNO": "Fresno", "PDX": "Portland",
    "RNO": "Reno", "DEN": "Denver", "SLC": "Salt Lake City",
}


def dest_city(code: str, name: str) -> str:
    """Short destination city for the board."""
    if code in DEST_CITY:
        return DEST_CITY[code]
    # Fallback for unmapped codes: trim a full station name to its lead token.
    return name.split("-")[0].split(",")[0].strip() or code


def train_number(train: dict) -> int:
    """Numeric part of trainNum/trainNumRaw, ignoring 'b'/'v' bus prefixes.

    Returns 0 if no digits are present.
    """
    for key in ("trainNumRaw", "trainNum"):
        m = re.search(r"\d+", str(train.get(key, "")))
        if m:
            return int(m.group())
    return 0


@dataclass
class Stop:
    train_num: int
    route: str
    dest: str              # short destination city (the "To")
    status: str            # e.g. "Enroute", "Departed", "Station"
    sch: datetime | None   # scheduled time we sort/label by (departure if present)
    est: datetime | None   # estimated/actual counterpart
    delay_min: int | None  # est - sch, rounded minutes (None if unknown)

    @property
    def is_late(self) -> bool:
        return self.delay_min is not None and self.delay_min >= 5

    @property
    def departed(self) -> bool:
        return self.status.lower() == "departed"


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def fetch_raw(url: str = TRAINS_URL) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_board(raw: dict, now: datetime | None = None) -> list[Stop]:
    """Return upcoming SAC stops, soonest first.

    "Upcoming" = the train has a SAC stop it hasn't departed yet. We key timing
    off the scheduled departure (falling back to arrival), and mark delay from
    whichever estimated/actual time is available.
    """
    now = now or _now()
    board: list[Stop] = []

    # /v3/trains is keyed by train number -> list of train instances.
    for trains in raw.values():
        for train in trains:
            if train.get("destCode") == STATION:
                continue  # terminates at SAC — an arrival, not a departure
            num = train_number(train)
            route = train.get("routeName") or (f"Train {num}" if num else "Amtrak")
            dest = dest_city(train.get("destCode", ""), train.get("destName", ""))
            for s in train.get("stations", []):
                if s.get("code") != STATION:
                    continue
                if s.get("bus"):
                    continue  # Thruway bus connection, not a train at the platform

                sch_dep, sch_arr = _parse(s.get("schDep")), _parse(s.get("schArr"))
                est_dep, est_arr = _parse(s.get("dep")), _parse(s.get("arr"))
                status = s.get("status", "") or ""

                # Prefer departure timing; fall back to arrival (terminus / arr-only).
                sch = sch_dep or sch_arr
                est = est_dep or est_arr if (sch_dep or est_dep) else est_arr
                if sch is None:
                    continue

                # Keep only stops in the window [now, now + MAX_HOURS]. Skips
                # past/departed trains and future days beyond the horizon.
                ref = est or sch
                if status.lower() == "departed" or ref < now:
                    continue
                if ref > now + timedelta(hours=MAX_HOURS):
                    continue

                delay = round((est - sch).total_seconds() / 60) if (est and sch) else None
                board.append(Stop(num, route, dest, status, sch, est, delay))
                break  # one SAC stop per train instance

    board.sort(key=lambda s: s.est or s.sch)

    # Dedupe: one departure per train per destination per scheduled day. The
    # feed lists each day's run separately; the window usually leaves just one,
    # but this guards against any same-day double-listing. Keep the soonest.
    seen: set = set()
    deduped: list[Stop] = []
    for s in board:
        key = (s.train_num, s.dest, s.sch.astimezone().date())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(s)
    return deduped


# Routes sourced from the GTFS schedule (full forward timetable) rather than
# the realtime-only Amtraker feed: Capitol Corridor and San Joaquins.
GTFS_ROUTES = {spec["route"] for spec in gtfs_sched.OPERATORS.values()}


def _is_gtfs_route(route: str) -> bool:
    return route in GTFS_ROUTES


def _gtfs_realtime_index(raw: dict) -> dict:
    """Realtime SAC departure delays for the GTFS-sourced routes, keyed by
    (train_num, local departure date) -> (delay_min, status, est)."""
    idx: dict = {}
    for trains in raw.values():
        for train in trains:
            if not _is_gtfs_route(train.get("routeName", "")):
                continue
            if train.get("destCode") == STATION:
                continue  # terminating at SAC — its SAC time is an arrival
            num = train_number(train)
            for s in train.get("stations", []):
                if s.get("code") != STATION or s.get("bus"):
                    continue
                sch, est = _parse(s.get("schDep")), _parse(s.get("dep"))
                if sch and est:
                    delay = round((est - sch).total_seconds() / 60)
                    idx[(num, sch.astimezone().date())] = (
                        delay, s.get("status", "") or "", est)
                break
    return idx


def _gtfs_board(raw: dict, now: datetime) -> list[Stop]:
    """All scheduled SAC departures for the GTFS routes in the window, with live
    Amtraker delays overlaid where a train is being tracked."""
    rt = _gtfs_realtime_index(raw)
    stops: list[Stop] = []
    for operator in gtfs_sched.OPERATORS:
        for num, route, dest, sched in gtfs_sched.scheduled_departures(
                now, MAX_HOURS, operator):
            delay, status, est = rt.get((num, sched.astimezone().date()),
                                        (None, "Scheduled", None))
            stops.append(Stop(num, route, dest, status, sched, est, delay))
    return stops


def get_board() -> list[Stop]:
    """Merged board: Capitol Corridor + San Joaquins from the published GTFS
    schedule (full forward timetable + live delays), long-distance trains
    (California Zephyr, Coast Starlight) from the Amtraker realtime feed.
    """
    raw = fetch_raw()
    now = _now()
    amtrak = build_board(raw, now)
    board = [s for s in amtrak if not _is_gtfs_route(s.route)]

    try:
        board += _gtfs_board(raw, now)
    except Exception as e:  # noqa: BLE001 - degrade to realtime-only if GTFS is down
        print(f"GTFS schedule unavailable, using realtime only: {e}",
              file=sys.stderr)
        board += [s for s in amtrak if _is_gtfs_route(s.route)]

    board.sort(key=lambda s: s.est or s.sch)

    # One departure per train per scheduled day across the merged sources.
    seen: set = set()
    out: list[Stop] = []
    for s in board:
        key = (s.train_num, s.sch.astimezone().date())
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


if __name__ == "__main__":
    for stop in get_board():
        local = (stop.est or stop.sch).astimezone()
        tag = (f"+{stop.delay_min}m LATE" if stop.is_late
               else "on time" if stop.delay_min is not None else "—")
        print(f"{local:%H:%M}  #{stop.train_num:<4} {stop.route:<18} "
              f"to {stop.dest:<14} {stop.status:<10} {tag}")
