#!/usr/bin/env python3
"""
Generates an activity-overview.svg that replicates GitHub's native
Activity Overview star/cross chart (Commits · Issues · PRs · Code review).
"""

import os
import sys
import requests

def fetch_contributions(token, username):
    query = """
    query($user: String!) {
      user(login: $user) {
        contributionsCollection {
          totalCommitContributions
          totalIssueContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
        }
      }
    }
    """
    resp = requests.post(
        "https://api.github.com/graphql",
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
        },
        json={"query": query, "variables": {"user": username}},
        timeout=15,
    )
    resp.raise_for_status()
    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(f"GraphQL errors: {payload['errors']}")
    col = payload["data"]["user"]["contributionsCollection"]
    return {
        "commits": col["totalCommitContributions"],
        "issues":  col["totalIssueContributions"],
        "prs":     col["totalPullRequestContributions"],
        "reviews": col["totalPullRequestReviewContributions"],
    }


def generate_svg(stats):
    commits = stats["commits"]
    issues  = stats["issues"]
    prs     = stats["prs"]
    reviews = stats["reviews"]

    total = commits + issues + prs + reviews or 1

    cp = commits / total
    ip = issues  / total
    pp = prs     / total
    rp = reviews / total

    def pct(v):
        return f"{round(v * 100)}%"

    # Layout
    W, H   = 460, 280
    cx, cy = 268, 140   # star center (shifted right to give space for "Commits" label)
    MAX_R  = 96          # maximum axis arm length in px
    MIN_R  = 6           # minimum arm length so tiny values still show

    def arm(p):
        return max(MIN_R, p * MAX_R)

    lx = cx - arm(cp)   # Commits  → left
    rx = cx + arm(ip)   # Issues   → right
    ty = cy - arm(rp)   # Code rev → top
    by = cy + arm(pp)   # PRs      → bottom

    poly = f"{lx},{cy} {cx},{ty} {rx},{cy} {cx},{by}"

    FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
    TEXT = "#e6edf3"
    MUTED = "#8b949e"
    GREEN = "#3fb950"
    GRID  = "#30363d"
    FILL  = "#1a7f37"

    return f"""\
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur in="SourceGraphic" stdDeviation="2.8" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="cglow" x="-120%" y="-120%" width="340%" height="340%">
      <feGaussianBlur in="SourceGraphic" stdDeviation="5.5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <!-- Card background -->
  <rect width="{W}" height="{H}" rx="6" fill="#0d1117"/>

  <!-- Crosshair grid lines -->
  <line x1="{cx - MAX_R - 6}" y1="{cy}" x2="{cx + MAX_R + 6}" y2="{cy}"
        stroke="{GRID}" stroke-width="1"/>
  <line x1="{cx}" y1="{cy - MAX_R - 6}" x2="{cx}" y2="{cy + MAX_R + 6}"
        stroke="{GRID}" stroke-width="1"/>

  <!-- Star fill -->
  <polygon points="{poly}" fill="{FILL}" fill-opacity="0.22"/>

  <!-- Star outline (glowing) -->
  <polygon points="{poly}" fill="none" stroke="{GREEN}" stroke-width="1.6"
           filter="url(#glow)"/>

  <!-- Arm-tip dots -->
  <circle cx="{lx}" cy="{cy}"  r="3.5" fill="{GREEN}" filter="url(#glow)"/>
  <circle cx="{rx}" cy="{cy}"  r="3.5" fill="{GREEN}" filter="url(#glow)"/>
  <circle cx="{cx}" cy="{ty}"  r="3.5" fill="{GREEN}" filter="url(#glow)"/>
  <circle cx="{cx}" cy="{by}"  r="3.5" fill="{GREEN}" filter="url(#glow)"/>

  <!-- Centre dot -->
  <circle cx="{cx}" cy="{cy}" r="5" fill="{GREEN}" filter="url(#cglow)"/>

  <!-- ── Labels ── -->

  <!-- Code review (top) -->
  <text x="{cx}" y="{cy - MAX_R - 18}"
        fill="{TEXT}" font-size="13" font-weight="600"
        font-family="{FONT}" text-anchor="middle">{pct(rp)}</text>
  <text x="{cx}" y="{cy - MAX_R - 5}"
        fill="{MUTED}" font-size="11"
        font-family="{FONT}" text-anchor="middle">Code review</text>

  <!-- Commits (left) -->
  <text x="{cx - MAX_R - 12}" y="{cy - 7}"
        fill="{TEXT}" font-size="13" font-weight="600"
        font-family="{FONT}" text-anchor="end">{pct(cp)}</text>
  <text x="{cx - MAX_R - 12}" y="{cy + 9}"
        fill="{MUTED}" font-size="11"
        font-family="{FONT}" text-anchor="end">Commits</text>

  <!-- Issues (right) -->
  <text x="{cx + MAX_R + 12}" y="{cy - 7}"
        fill="{TEXT}" font-size="13" font-weight="600"
        font-family="{FONT}" text-anchor="start">{pct(ip)}</text>
  <text x="{cx + MAX_R + 12}" y="{cy + 9}"
        fill="{MUTED}" font-size="11"
        font-family="{FONT}" text-anchor="start">Issues</text>

  <!-- Pull requests (bottom) -->
  <text x="{cx}" y="{cy + MAX_R + 17}"
        fill="{TEXT}" font-size="13" font-weight="600"
        font-family="{FONT}" text-anchor="middle">{pct(pp)}</text>
  <text x="{cx}" y="{cy + MAX_R + 31}"
        fill="{MUTED}" font-size="11"
        font-family="{FONT}" text-anchor="middle">Pull requests</text>
</svg>
"""


if __name__ == "__main__":
    token    = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    username = os.environ.get("GH_USER", "parasmani-dev")

    if not token:
        print("ERROR: GH_TOKEN env var not set", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching contributions for {username}…")
    stats = fetch_contributions(token, username)
    print(f"  commits={stats['commits']}  issues={stats['issues']}"
          f"  prs={stats['prs']}  reviews={stats['reviews']}")

    svg = generate_svg(stats)

    out = "activity-overview.svg"
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Saved {out}")
