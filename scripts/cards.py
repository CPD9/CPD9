"""Profile cards for github.com/CPD9, drawn from the GitHub GraphQL API.

Writes assets/{year,balance}-{dark,light}.svg. Standard library only, so the
daily workflow needs nothing installed. Run: GITHUB_TOKEN=... python3 scripts/cards.py
"""

from __future__ import annotations

import json
import math
import os
import urllib.request
from datetime import date
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


def balance_card(year: dict, theme: dict) -> str:
    """Commits, pull requests and reviews as a triangle, each scaled to the largest."""
    corners = [
        ("Commits", year["totalCommitContributions"], "building", -90),
        ("Pull requests", year["totalPullRequestContributions"], "shipping", 30),
        ("Reviews", year["totalPullRequestReviewContributions"], "reviewing", 150),
    ]
    top = max(value for _, value, _, _ in corners) or 1
    cx, cy, radius = 360, 104, 70

    def point(angle: float, length: float) -> tuple[float, float]:
        return (cx + length * math.cos(math.radians(angle)),
                cy + length * math.sin(math.radians(angle)))

    def polygon(points) -> str:
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)

    parts = [
        text(24, 36, "HOW I CONTRIBUTE", 11, theme["muted"], 600, spacing=1.2),
        text(24, 62, "Last 12 months, each corner", 12, theme["muted"]),
        text(24, 78, "scaled to the largest", 12, theme["muted"]),
    ]
    for i, (label, value, verb, _) in enumerate(corners):
        y = 112 + i * 26
        parts.append(f'<rect x="24" y="{y - 12}" width="2" height="20" fill="{theme["accent"]}"/>')
        parts.append(text(34, y + 3, f"{value:,}", 14, theme["text"], 600))
        parts.append(text(80, y + 3, f"{label.lower()}, {verb}", 11, theme["muted"]))
    for ring in (1 / 3, 2 / 3, 1):
        outline = polygon(point(angle, radius * ring) for *_, angle in corners)
        parts.append(f'<polygon points="{outline}" fill="none" stroke="{theme["line"]}"/>')
    for *_, angle in corners:
        x, y = point(angle, radius)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{theme["line"]}"/>')
    shape = [point(angle, radius * value / top) for _, value, _, angle in corners]
    parts.append(
        f'<polygon points="{polygon(shape)}" fill="{theme["accent"]}" fill-opacity="0.28" '
        f'stroke="{theme["accent"]}" stroke-width="2" stroke-linejoin="round"/>'
    )
    for x, y in shape:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{theme["accent"]}"/>')
    labels = [(cx, cy - radius - 10), (cx + radius * 0.87 + 6, cy + radius / 2 + 18),
              (cx - radius * 0.87 - 6, cy + radius / 2 + 18)]
    for (x, y), (label, *_) in zip(labels, corners):
        parts.append(text(x, y, label, 11, theme["text"], 600, anchor="middle"))
    return frame(495, 195, f"{LOGIN}: balance of commits, pull requests and reviews", "".join(parts), theme)


def main() -> None:
    year = graphql(YEAR, {"login": LOGIN})["user"]["contributionsCollection"]
    OUT.mkdir(exist_ok=True)
    for name, theme in THEMES.items():
        (OUT / f"year-{name}.svg").write_text(year_card(year, theme))
        (OUT / f"balance-{name}.svg").write_text(balance_card(year, theme))
    print(f"cards written: {year['contributionCalendar']['totalContributions']} contributions")


if __name__ == "__main__":
    main()
