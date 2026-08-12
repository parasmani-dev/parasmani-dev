#!/usr/bin/env python3
"""
Generates activity-overview.svg â€” replicates GitHub's native Activity Overview
star/cross chart (Commits Â· Issues Â· PRs Â· Code review).

Labels float near their arm tips (not fixed at MAX_R),
and arm lengths use sqrt-scaling so even tiny percentages are visible.
"""

import math
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
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
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

    def pct_str(v):
        return f"{round(v * 100)}%"

    # â”€â”€ Layout â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    W, H     = 480, 300
    cx, cy   = 270, 150    # star centre (right-of-centre to give room for Commits label)
    MAX_R    = 100          # full axis arm length (crosshair grid lines)
    MIN_VIS  = 8            # minimum coloured-arm length so tiny values stay visible

    # Sqrt-scale: preserves relative magnitude but lifts tiny values off zero.
    def arm_len(p):
        return max(MIN_VIS, math.sqrt(p) * MAX_R)

    # Arm-tip coordinates
    lx = cx - arm_len(cp)   # Commits  â†’ left
    rx = cx + arm_len(ip)   # Issues   â†’ right
    ty = cy - arm_len(rp)   # Code rev â†’ top
    by = cy + arm_len(pp)   # PRs      â†’ bottom

    poly = f"{lx:.2f},{cy} {cx},{ty:.2f} {rx:.2f},{cy} {cx},{by:.2f}"

    # â”€â”€ Colours & font â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    FONT  = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
    TEXT  = "#e6edf3"
    MUTED = "#8b949e"
    GREEN = "#3fb950"
    GRID  = "#30363d"
    FILL  = "#1a7f37"

    # â”€â”€ Label positions (near arm tips) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PAD = 14    # px gap between arm tip and nearest edge of label

    # Commits (left arm) â€” text anchored to end, centred vertically on arm tip
    lbl_commits_x  = lx - PAD
    lbl_commits_y1 = cy - 7    # percentage line
    lbl_commits_y2 = cy + 9    # "Commits" line

    # Issues (right arm) â€” text anchored to start
    lbl_issues_x   = rx + PAD
    lbl_issues_y1  = cy - 7
    lbl_issues_y2  = cy + 9

    # Code review (top arm) â€” text centred above arm tip
    lbl_review_x   = cx
    lbl_review_y1  = ty - PAD - 4    # percentage
    lbl_review_y2  = ty - PAD + 9    # "Code review"

    # Pull requests (bottom arm) â€” text centred below arm tip
    lbl_pr_x        = cx
    lbl_pr_y1       = by + PAD + 4    # percentage
    lbl_pr_y2       = by + PAD + 18   # "Pull requests"

    # Clamp labels inside SVG bounds
    def clamp_y(y, lo=14, hi=H - 6):
        return max(lo, min(hi, y))

    lbl_review_y1 = clamp_y(lbl_review_y1)
    lbl_review_y2 = clamp_y(lbl_review_y2)
    lbl_pr_y1     = clamp_y(lbl_pr_y1)
    lbl_pr_y2     = clamp_y(lbl_pr_y2)

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

  <!-- Full crosshair grid lines (show max scale) -->
  <line x1="{cx - MAX_R}" y1="{cy}" x2="{cx + MAX_R}" y2="{cy}"
        stroke="{GRID}" stroke-width="1"/>
  <line x1="{cx}" y1="{cy - MAX_R}" x2="{cx}" y2="{cy + MAX_R}"
        stroke="{GRID}" stroke-width="1"/>

  <!-- Star fill -->
  <polygon points="{poly}" fill="{FILL}" fill-opacity="0.25"/>

  <!-- Star outline with glow -->
  <polygon points="{poly}" fill="none" stroke="{GREEN}" stroke-width="1.8"
           filter="url(#glow)"/>

  <!-- Arm-tip dots -->
  <circle cx="{lx:.2f}" cy="{cy}"    r="3.5" fill="{GREEN}" filter="url(#glow)"/>
  <circle cx="{rx:.2f}" cy="{cy}"    r="3.5" fill="{GREEN}" filter="url(#glow)"/>
  <circle cx="{cx}"     cy="{ty:.2f}" r="3.5" fill="{GREEN}" filter="url(#glow)"/>
  <circle cx="{cx}"     cy="{by:.2f}" r="3.5" fill="{GREEN}" filter="url(#glow)"/>

  <!-- Centre dot -->
  <circle cx="{cx}" cy="{cy}" r="5" fill="{GREEN}" filter="url(#cglow)"/>

  <!-- â”€â”€ Labels near arm tips â”€â”€ -->

  <!-- Code review (top) -->
  <text x="{lbl_review_x}" y="{lbl_review_y1:.1f}"
        fill="{TEXT}" font-size="13" font-weight="600"
        font-family="{FONT}" text-anchor="middle">{pct_str(rp)}</text>
  <text x="{lbl_review_x}" y="{lbl_review_y2:.1f}"
        fill="{MUTED}" font-size="11"
        font-family="{FONT}" text-anchor="middle">Code review</text>

  <!-- Commits (left) -->
  <text x="{lbl_commits_x:.2f}" y="{lbl_commits_y1}"
        fill="{TEXT}" font-size="13" font-weight="600"
        font-family="{FONT}" text-anchor="end">{pct_str(cp)}</text>
  <text x="{lbl_commits_x:.2f}" y="{lbl_commits_y2}"
        fill="{MUTED}" font-size="11"
        font-family="{FONT}" text-anchor="end">Commits</text>

  <!-- Issues (right) -->
  <text x="{lbl_issues_x:.2f}" y="{lbl_issues_y1}"
        fill="{TEXT}" font-size="13" font-weight="600"
        font-family="{FONT}" text-anchor="start">{pct_str(ip)}</text>
  <text x="{lbl_issues_x:.2f}" y="{lbl_issues_y2}"
        fill="{MUTED}" font-size="11"
        font-family="{FONT}" text-anchor="start">Issues</text>

  <!-- Pull requests (bottom) -->
  <text x="{lbl_pr_x}" y="{lbl_pr_y1:.1f}"
        fill="{TEXT}" font-size="13" font-weight="600"
        font-family="{FONT}" text-anchor="middle">{pct_str(pp)}</text>
  <text x="{lbl_pr_x}" y="{lbl_pr_y2:.1f}"
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

    print(f"Fetching contributions for {username}â€¦")
    stats = fetch_contributions(token, username)
    total = stats['commits'] + stats['issues'] + stats['prs'] + stats['reviews']
    print(f"  commits={stats['commits']} ({stats['commits']/total*100:.0f}%)"
          f"  issues={stats['issues']} ({stats['issues']/total*100:.0f}%)"
          f"  prs={stats['prs']} ({stats['prs']/total*100:.0f}%)"
          f"  reviews={stats['reviews']} ({stats['reviews']/total*100:.0f}%)")

    svg = generate_svg(stats)

    out = "activity-overview.svg"
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"âœ…  Saved {out}")
