"""Profile cards for github.com/CPD9, drawn from the GitHub GraphQL API.

Writes assets/{totals,averages}-{dark,light}.svg. Standard library only, so the
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


def heat_level(value: float, peak: float) -> int:
    """0 for nothing, then four steps; the square root keeps quiet weeks visible."""
    if value <= 0:
        return 0
    return min(4, 1 + int(3.999 * (value / max(peak, 1e-9)) ** 0.5))


def rise(delay: float, inner: str) -> str:
    return f'<g class="rise" style="animation-delay:{delay:.2f}s">{inner}</g>'


def totals_card(year: dict, theme: dict) -> str:
    """The year's numbers on the left; commits, PRs and reviews as a triangle on the right."""
    total = year["contributionCalendar"]["totalContributions"]
    parts = [
        rise(0, text(28, 40, "LAST 12 MONTHS", 11, theme["muted"], 600, spacing=1.4)
             + text(28, 96, f"{total:,}", 48, theme["text"], 700)
             + text(28, 120, "contributions", 13, theme["muted"])),
    ]
    stats = [
        ("commits", year["totalCommitContributions"]),
        ("pull requests", year["totalPullRequestContributions"]),
        ("reviews", year["totalPullRequestReviewContributions"]),
        ("issues", year["totalIssueContributions"]),
    ]
    for i, (label, value) in enumerate(stats):
        x = 28 + i * 118
        parts.append(rise(0.15 + i * 0.1,
            f'<rect x="{x}" y="150" width="2" height="34" fill="{theme["accent"]}"/>'
            + text(x + 10, 166, f"{value:,}", 18, theme["text"], 600)
            + text(x + 10, 182, label, 11, theme["muted"])))

    corners = [
        ("Commits", year["totalCommitContributions"], -90),
        ("Pull requests", year["totalPullRequestContributions"], 30),
        ("Reviews", year["totalPullRequestReviewContributions"], 150),
    ]
    top = max(value for _, value, _ in corners) or 1
    cx, cy, radius = 680, 120, 78

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
    return frame(860, 220, f"{LOGIN}: contributions in the last 12 months", "".join(parts), theme)


def averages(year: dict) -> dict:
    """Average contributions a day, three ways: by week, by weekday, by month."""
    days = {date.fromisoformat(d["date"]): d["contributionCount"]
            for w in year["contributionCalendar"]["weeks"] for d in w["contributionDays"]}
    ordered = sorted(days)
    mean = lambda xs: sum(days[d] for d in xs) / len(xs) if xs else 0.0
    weeks = [ordered[len(ordered) - (i + 1) * 7:len(ordered) - i * 7] for i in range(9)][::-1]
    by_weekday = [[d for d in ordered if d.isoweekday() == k] for k in range(1, 8)]
    today = ordered[-1]
    months, y, m = [], today.year, today.month
    for _ in range(9):
        months.append((date(y, m, 1), mean([d for d in ordered if (d.year, d.month) == (y, m)])))
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    months.reverse()
    return {
        "weeks": [mean(w) for w in weeks],
        "weekday": [mean(w) for w in by_weekday],
        "weekdays": mean([d for w in by_weekday[:5] for d in w]),
        "weekend": mean([d for w in by_weekday[5:] for d in w]),
        "months": months,
    }


def averages_card(avg: dict, theme: dict) -> str:
    """An isometric cube: top face by week, left by weekday, right by month."""
    top = avg["weeks"]
    left = avg["weekday"] + [avg["weekdays"], avg["weekend"]]
    right = [value for _, value in avg["months"]]
    peak = max(top + left + right) or 1
    s, cx, cy = 28, 150, 110
    a, b, d = (-0.866 * s, -0.5 * s), (0.866 * s, -0.5 * s), (0, s)
    parts = []

    def face(values, u, v, shade, start):
        for k, value in enumerate(values):
            i, j = k // 3, k % 3
            corners = [(i + x, j + y) for x, y in ((0.09, 0.09), (0.91, 0.09), (0.91, 0.91), (0.09, 0.91))]
            poly = " ".join(f"{cx + u[0] * p + v[0] * q:.1f},{cy + u[1] * p + v[1] * q:.1f}" for p, q in corners)
            parts.append(
                f'<g class="cell" style="animation-delay:{start + k * 0.07:.2f}s">'
                f'<polygon points="{poly}" fill="{theme["heat"][heat_level(value, peak)]}" '
                f'stroke="{theme["line"]}" stroke-width="0.6" stroke-linejoin="round"/>'
                f'<polygon points="{poly}" fill="#000" fill-opacity="{shade}"/></g>'
            )

    face(top, b, a, 0.0, 0.2)
    face(left, d, a, 0.1, 0.8)
    face(right, d, b, 0.22, 1.4)

    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    busiest = max(range(7), key=lambda k: avg["weekday"][k])
    first_month, first_value = avg["months"][0]
    trend = "up" if right[-1] >= first_value else "down"
    lines = [
        ("TOP", "last 9 weeks", f"{top[-1]:.1f} a day this week, {sum(top) / len(top):.1f} on average"),
        ("LEFT", "by weekday", f"busiest {names[busiest]} at {avg['weekday'][busiest]:.1f}; "
                               f"weekdays {avg['weekdays']:.1f}, weekends {avg['weekend']:.1f}"),
        ("RIGHT", "last 9 months", f"{right[-1]:.1f} a day this month, {trend} from {first_value:.1f} "
                                   f"in {first_month:%B}"),
    ]
    x0 = 320
    parts.append(rise(0, text(x0, 40, "HOW I SHOW UP, AVERAGE CONTRIBUTIONS A DAY", 11, theme["muted"], 600, spacing=1.4)))
    for n, (side, what, line) in enumerate(lines):
        y = 86 + n * 46
        parts.append(rise(0.3 + n * 0.25,
            f'<rect x="{x0}" y="{y - 14}" width="2" height="32" fill="{theme["accent"]}"/>'
            + text(x0 + 10, y, f"{side} · {what}", 11, theme["muted"], 600, spacing=0.6)
            + text(x0 + 10, y + 16, line, 14, theme["text"], 600)))
    return frame(860, 220, f"{LOGIN}: average contributions a day, as a cube", "".join(parts), theme)


def main() -> None:
    year = graphql(YEAR, {"login": LOGIN})["user"]["contributionsCollection"]
    avg = averages(year)
    OUT.mkdir(exist_ok=True)
    for name, theme in THEMES.items():
        (OUT / f"totals-{name}.svg").write_text(totals_card(year, theme))
        (OUT / f"averages-{name}.svg").write_text(averages_card(avg, theme))
    print(f"cards written: {year['contributionCalendar']['totalContributions']} contributions")


if __name__ == "__main__":
    main()
