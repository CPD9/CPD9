"""Profile cards for github.com/CPD9, drawn from the GitHub GraphQL API.

Writes assets/{year,streak}-{dark,light}.svg. Standard library only, so the
daily workflow needs nothing installed. Run: GITHUB_TOKEN=... python3 scripts/cards.py
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

LOGIN = os.environ.get("PROFILE_LOGIN", "CPD9")
OUT = Path(__file__).resolve().parent.parent / "assets"

THEMES = {
    "dark": {
        "text": "#e6edf3",
        "muted": "#8b949e",
        "line": "#30363d",
        "accent": "#3fb8a5",
        "heat": ["#161b22", "#0e4d45", "#14766a", "#25a08f", "#5fd3c0"],
    },
    "light": {
        "text": "#1f2328",
        "muted": "#59636e",
        "line": "#d1d9e0",
        "accent": "#0f7b6c",
        "heat": ["#eff2f5", "#b5e3da", "#6cc4b3", "#2a9d8a", "#0f6b5e"],
    },
}
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


def graphql(query: str, variables: dict) -> dict:
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": f"bearer {os.environ['GITHUB_TOKEN']}",
            "Content-Type": "application/json",
            "User-Agent": f"{LOGIN}-profile-cards",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    if body.get("errors"):
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]


YEAR = """
query($login: String!) {
  user(login: $login) {
    createdAt
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

SPAN = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""


def days_of(calendar: dict) -> dict[date, int]:
    return {
        date.fromisoformat(day["date"]): day["contributionCount"]
        for week in calendar["weeks"]
        for day in week["contributionDays"]
    }


def all_days(created: date, today: date) -> dict[date, int]:
    """Every day since the account was made, one year-long query at a time."""
    days: dict[date, int] = {}
    start = created
    while start <= today:
        end = min(start + timedelta(days=364), today)
        data = graphql(
            SPAN,
            {
                "login": LOGIN,
                "from": f"{start.isoformat()}T00:00:00Z",
                "to": f"{end.isoformat()}T23:59:59Z",
            },
        )
        days.update(days_of(data["user"]["contributionsCollection"]["contributionCalendar"]))
        start = end + timedelta(days=1)
    return {day: count for day, count in days.items() if day <= today}


def streaks(days: dict[date, int], today: date) -> dict:
    """Current streak may end yesterday: today is still being written."""
    ordered = sorted(days)
    longest = (0, None, None)
    run, run_start = 0, None
    for day in ordered:
        if days[day] > 0:
            run_start = day if run == 0 else run_start
            run += 1
            if run > longest[0]:
                longest = (run, run_start, day)
        else:
            run = 0
    end = today if days.get(today, 0) > 0 else today - timedelta(days=1)
    current, cursor = 0, end
    while days.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    return {
        "current": current,
        "current_from": cursor + timedelta(days=1) if current else None,
        "longest": longest[0],
        "longest_from": longest[1],
        "longest_to": longest[2],
    }


def short(day: date | None) -> str:
    return day.strftime("%-d %b %Y") if day else "none yet"


def span(start: date | None, end: date | None) -> str:
    if not start or not end:
        return "none yet"
    first = start.strftime("%-d %b") if start.year == end.year else short(start)
    return f"{first} to {short(end)}"


def text(x, y, value, size, colour, weight=400, anchor="start", spacing=0):
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
        f'font-weight="{weight}" fill="{colour}" text-anchor="{anchor}" '
        f'letter-spacing="{spacing}">{escape(str(value))}</text>'
    )


def frame(width, height, title, body, theme):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">'
        f"<title>{escape(title)}</title>"
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" '
        f'fill="none" stroke="{theme["line"]}"/>{body}</svg>'
    )


def heat_level(count: int, top: int) -> int:
    if count == 0:
        return 0
    return min(4, 1 + int(3 * count / max(top, 1)))


def year_card(year: dict, theme: dict) -> str:
    calendar = year["contributionCalendar"]
    weeks = calendar["weeks"][-26:]
    counts = [d["contributionCount"] for w in weeks for d in w["contributionDays"]]
    top = sorted(counts)[int(len(counts) * 0.95)] if counts else 1
    parts = [
        text(24, 36, "LAST 12 MONTHS", 11, theme["muted"], 600, spacing=1.2),
        text(24, 84, f"{calendar['totalContributions']:,}", 42, theme["text"], 600),
        text(24, 106, "contributions", 13, theme["muted"]),
    ]
    stats = [
        ("Commits", year["totalCommitContributions"]),
        ("Pull requests", year["totalPullRequestContributions"]),
        ("Reviews", year["totalPullRequestReviewContributions"]),
        ("Issues", year["totalIssueContributions"]),
    ]
    for i, (label, value) in enumerate(stats):
        x = 24 + i * 112
        parts.append(f'<rect x="{x}" y="132" width="2" height="34" fill="{theme["accent"]}"/>')
        parts.append(text(x + 10, 148, f"{value:,}", 16, theme["text"], 600))
        parts.append(text(x + 10, 164, label, 11, theme["muted"]))
    # 26 columns must end inside the 495px card with a 28px margin.
    cell, gap, left, topy = 8, 2.5, 196, 24
    for wi, week in enumerate(weeks):
        for day in week["contributionDays"]:
            row = date.fromisoformat(day["date"]).isoweekday() % 7
            colour = theme["heat"][heat_level(day["contributionCount"], top)]
            parts.append(
                f'<rect x="{left + wi * (cell + gap)}" y="{topy + row * (cell + gap)}" '
                f'width="{cell}" height="{cell}" rx="2" fill="{colour}"/>'
            )
    parts.append(
        text(left + 26 * (cell + gap) - gap, topy + 7 * (cell + gap) + 12,
             "last 26 weeks", 10, theme["muted"], anchor="end")
    )
    return frame(495, 195, f"{LOGIN}: contributions in the last 12 months", "".join(parts), theme)


def streak_card(s: dict, active: int, theme: dict) -> str:
    """The ring is the current streak against the longest: full means a record run."""
    share = s["current"] / s["longest"] if s["longest"] else 0
    r, cx, cy = 46, 404, 92
    circumference = 2 * 3.14159265 * r
    record = s["current"] and s["current"] == s["longest"]
    parts = [
        text(24, 36, "STREAK", 11, theme["muted"], 600, spacing=1.2),
        text(24, 84, f"{s['current']}", 42, theme["text"], 600),
        text(24, 106, "days in a row" if s["current"] != 1 else "day in a row", 13, theme["muted"]),
        text(24, 124, f"since {short(s['current_from'])}" if s["current"] else "starts with the next contribution", 11, theme["muted"]),
        f'<rect x="24" y="138" width="2" height="34" fill="{theme["accent"]}"/>',
        text(34, 154, f"{s['longest']} days", 16, theme["text"], 600),
        text(34, 170, f"longest, {span(s['longest_from'], s['longest_to'])}", 11, theme["muted"]),
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{theme["heat"][0]}" stroke-width="8"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{theme["accent"]}" stroke-width="8" '
        f'stroke-linecap="round" stroke-dasharray="{circumference * share:.1f} {circumference:.1f}" '
        f'transform="rotate(-90 {cx} {cy})"/>',
        text(cx, cy - 2, "record" if record else f"{round(share * 100)}%", 16 if record else 20, theme["text"], 600, anchor="middle"),
        text(cx, cy + 16, "run" if record else "of record", 11, theme["muted"], anchor="middle"),
        text(cx, cy + r + 22, f"{active} of 365 days active", 11, theme["muted"], anchor="middle"),
    ]
    return frame(495, 195, f"{LOGIN}: contribution streak", "".join(parts), theme)


def main() -> None:
    today = datetime.now(timezone.utc).date()
    user = graphql(YEAR, {"login": LOGIN})["user"]
    year = user["contributionsCollection"]
    created = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00")).date()
    days = all_days(created, today)
    s = streaks(days, today)
    active = sum(1 for d, count in days.items() if count > 0 and (today - d).days < 365)
    OUT.mkdir(exist_ok=True)
    for name, theme in THEMES.items():
        (OUT / f"year-{name}.svg").write_text(year_card(year, theme))
        (OUT / f"streak-{name}.svg").write_text(streak_card(s, active, theme))
    print(f"cards written: {year['contributionCalendar']['totalContributions']} contributions, "
          f"streak {s['current']}, longest {s['longest']}, active {active}/365")


if __name__ == "__main__":
    main()
