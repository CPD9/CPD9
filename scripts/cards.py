"""Profile cards for github.com/CPD9, drawn from the GitHub GraphQL API.

Writes assets/dashboard-{dark,light}.svg. Standard library only, so the
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


MOTION = """<style>
.rise{opacity:0;animation:rise .6s ease-out forwards}
@keyframes rise{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.shape{transform:scale(0);animation:grow 1.2s cubic-bezier(.2,.8,.2,1) .4s forwards}
@keyframes grow{to{transform:scale(1)}}
.cell{opacity:0;animation:fade .3s ease-out forwards}
@keyframes fade{to{opacity:1}}
@media (prefers-reduced-motion:reduce){.rise,.shape,.cell{animation:none;opacity:1;transform:none}}
</style>"""


def frame(width, height, title, body, theme):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">'
        f"<title>{escape(title)}</title>{MOTION}"
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" '
        f'fill="none" stroke="{theme["line"]}"/>{body}</svg>'
    )


def heat_level(count: int, top: int) -> int:
    if count == 0:
        return 0
    return min(4, 1 + int(3 * count / max(top, 1)))


def dashboard_card(year: dict, theme: dict) -> str:
    """Numbers on the left, the commit/PR/review triangle in the middle, the grid on the right."""
    calendar = year["contributionCalendar"]
    total = calendar["totalContributions"]
    parts = [
        f'<g class="rise">{text(28, 40, "LAST 12 MONTHS", 11, theme["muted"], 600, spacing=1.4)}'
        f'{text(28, 94, f"{total:,}", 48, theme["text"], 700)}'
        f'{text(28, 118, "contributions", 13, theme["muted"])}</g>',
    ]
    stats = [
        ("commits", year["totalCommitContributions"]),
        ("pull requests", year["totalPullRequestContributions"]),
        ("reviews", year["totalPullRequestReviewContributions"]),
        ("issues", year["totalIssueContributions"]),
    ]
    for i, (label, value) in enumerate(stats):
        x, y = 28 + (i % 2) * 124, 158 + (i // 2) * 40
        parts.append(
            f'<g class="rise" style="animation-delay:{0.15 + i * 0.1:.2f}s">'
            f'<rect x="{x}" y="{y - 14}" width="2" height="30" fill="{theme["accent"]}"/>'
            f'{text(x + 10, y, f"{value:,}", 16, theme["text"], 600)}'
            f'{text(x + 10, y + 14, label, 11, theme["muted"])}</g>'
        )

    corners = [
        ("Commits", year["totalCommitContributions"], -90),
        ("Pull requests", year["totalPullRequestContributions"], 30),
        ("Reviews", year["totalPullRequestReviewContributions"], 150),
    ]
    top = max(value for _, value, _ in corners) or 1
    cx, cy, radius = 400, 124, 74

    def point(angle: float, length: float) -> tuple[float, float]:
        return (cx + length * math.cos(math.radians(angle)),
                cy + length * math.sin(math.radians(angle)))

    def polygon(points) -> str:
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)

    for ring in (1 / 3, 2 / 3, 1):
        outline = polygon(point(angle, radius * ring) for *_, angle in corners)
        parts.append(f'<polygon points="{outline}" fill="none" stroke="{theme["line"]}"/>')
    for *_, angle in corners:
        x, y = point(angle, radius)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{theme["line"]}"/>')
    shape = [point(angle, radius * value / top) for _, value, angle in corners]
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{theme["accent"]}"/>' for x, y in shape)
    parts.append(
        f'<g class="shape" style="transform-origin:{cx}px {cy}px">'
        f'<polygon points="{polygon(shape)}" fill="{theme["accent"]}" fill-opacity="0.3" '
        f'stroke="{theme["accent"]}" stroke-width="2" stroke-linejoin="round"/>{dots}</g>'
    )
    labels = [(cx, cy - radius - 10), (cx + radius * 0.87 + 4, cy + radius / 2 + 20),
              (cx - radius * 0.87 - 4, cy + radius / 2 + 20)]
    for (x, y), (label, *_) in zip(labels, corners):
        parts.append(text(x, y, label, 11, theme["text"], 600, anchor="middle"))

    weeks = calendar["weeks"][-26:]
    counts = [d["contributionCount"] for w in weeks for d in w["contributionDays"]]
    peak = sorted(counts)[int(len(counts) * 0.95)] if counts else 1
    # 26 columns end 28px inside the 860px card.
    cell, gap, left, top_y = 10, 3, 860 - 28 - (26 * 13 - 3), 60
    for wi, week in enumerate(weeks):
        for day in week["contributionDays"]:
            row = date.fromisoformat(day["date"]).isoweekday() % 7
            colour = theme["heat"][heat_level(day["contributionCount"], peak)]
            parts.append(
                f'<rect class="cell" style="animation-delay:{0.3 + wi * 0.035:.3f}s" '
                f'x="{left + wi * (cell + gap)}" y="{top_y + row * (cell + gap)}" '
                f'width="{cell}" height="{cell}" rx="2" fill="{colour}"/>'
            )
    right = left + 26 * (cell + gap) - gap
    parts.append(text(left, top_y - 14, "LAST 26 WEEKS", 11, theme["muted"], 600, spacing=1.4))
    # Legend ends flush with the grid: "less" squares "more".
    legend_y = top_y + 7 * (cell + gap) + 12
    squares_end = right - 30
    parts.append(text(squares_end - 5 * (cell + gap) - 4, legend_y + 9, "less", 10, theme["muted"], anchor="end"))
    for i, colour in enumerate(theme["heat"]):
        parts.append(f'<rect x="{squares_end - (5 - i) * (cell + gap) + gap}" y="{legend_y}" '
                     f'width="{cell}" height="{cell}" rx="2" fill="{colour}"/>')
    parts.append(text(right, legend_y + 9, "more", 10, theme["muted"], anchor="end"))
    return frame(860, 230, f"{LOGIN}: contributions in the last 12 months", "".join(parts), theme)


def main() -> None:
    year = graphql(YEAR, {"login": LOGIN})["user"]["contributionsCollection"]
    OUT.mkdir(exist_ok=True)
    for name, theme in THEMES.items():
        (OUT / f"dashboard-{name}.svg").write_text(dashboard_card(year, theme))
    print(f"cards written: {year['contributionCalendar']['totalContributions']} contributions")


if __name__ == "__main__":
    main()
