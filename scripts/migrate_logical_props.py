"""
US-009 — Migrate directional CSS to logical properties (RTL support).

Conservative regex-based migration. Targets:
  margin-left   → margin-inline-start
  margin-right  → margin-inline-end
  padding-left  → padding-inline-start
  padding-right → padding-inline-end
  border-left   → border-inline-start
  border-right  → border-inline-end
  text-align: left  → text-align: start
  text-align: right → text-align: end
  float: left   → float: inline-start
  float: right  → float: inline-end
  STANDALONE  ^\s*left:    → inset-inline-start:
  STANDALONE  ^\s*right:   → inset-inline-end:
              (only at start of line / after { or ; - never inside other properties)

Skips: keys like `transform-origin: left`, anything in <template>/<script> blocks,
       border-LEFT-RADIUS-XYZ properties etc. handled because we match
       'border-left' followed by '-' too.

Usage : python scripts/migrate_logical_props.py [--dry-run] [file1 file2 ...]
        Without args, processes the curated 15-files list.
Outputs per-file count + total.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent

# Curated 15-files prioritized by directional CSS density (US-009 AC)
PRIORITY_FILES = [
    "frontend/src/components/Step3Simulation.vue",
    "frontend/src/components/HistoryDatabase.vue",
    "frontend/src/components/GraphPanel.vue",
    "frontend/src/components/Step4Report.vue",
    "frontend/src/components/Step2EnvSetup.vue",
    "frontend/src/components/Step5Interaction.vue",
    "frontend/src/views/ReplayView.vue",
    "frontend/src/views/Home.vue",
    "frontend/src/components/Step1GraphBuild.vue",
    "frontend/src/components/PolymarketChart.vue",
    "frontend/src/components/SettingsPanel.vue",
    "frontend/src/components/DebugPanel.vue",
    "frontend/src/views/SimulationView.vue",
    "frontend/src/views/ExploreView.vue",
    "frontend/src/components/CounterfactualBranchPanel.vue",
]

# Regex pairs (pattern, replacement). Keep ordered: longer/more-specific first.
# Word boundary on left edge avoids matching the trailing portion of other words.
SHORTHAND_RULES = [
    (r"\bmargin-left\b",   "margin-inline-start"),
    (r"\bmargin-right\b",  "margin-inline-end"),
    (r"\bpadding-left\b",  "padding-inline-start"),
    (r"\bpadding-right\b", "padding-inline-end"),
    (r"\bborder-left\b",   "border-inline-start"),
    (r"\bborder-right\b",  "border-inline-end"),
]

VALUE_RULES = [
    # text-align: left → text-align: start
    (re.compile(r"\b(text-align\s*:\s*)left\b"),  r"\1start"),
    (re.compile(r"\b(text-align\s*:\s*)right\b"), r"\1end"),
    # float: left/right → float: inline-start/end
    (re.compile(r"\b(float\s*:\s*)left\b"),  r"\1inline-start"),
    (re.compile(r"\b(float\s*:\s*)right\b"), r"\1inline-end"),
]

# Standalone positioning : `left: <val>;` or `right: <val>;`
# Match start-of-line (with optional whitespace) OR after `{`/`;` (block start
# or previous declaration). Avoid matching inside `border-left:` etc.
# Use lookbehind for negative-context : (?<![-\w]) ensures no letter/dash before.
STANDALONE_LEFT  = re.compile(r"(?<![-\w])left\s*:")
STANDALONE_RIGHT = re.compile(r"(?<![-\w])right\s*:")

# Only apply standalone replacement on lines NOT inside a property name (e.g. `transition: left 200ms`).
# Heuristic: only on declaration lines where `left:` or `right:` is the FIRST property of the line.
# We process line-by-line and check the line starts with optional whitespace, then `left:`/`right:`.
LINE_LEFT_DECL  = re.compile(r"^(\s*)left\s*:")
LINE_RIGHT_DECL = re.compile(r"^(\s*)right\s*:")

# Skip <template> and <script> blocks in .vue files (only touch <style> sections).
STYLE_BLOCK_RE = re.compile(r"(<style[^>]*>)([\s\S]*?)(</style>)", re.IGNORECASE)


def process_css(css: str) -> tuple[str, int]:
    """Apply all rules to a CSS string. Returns (new_css, replacement_count)."""
    n = 0
    # Shorthand props: word-boundary substitution
    for pat, repl in SHORTHAND_RULES:
        new_css, count = re.subn(pat, repl, css)
        n += count
        css = new_css
    # Value rules
    for pat, repl in VALUE_RULES:
        new_css, count = pat.subn(repl, css)
        n += count
        css = new_css
    # Standalone left:/right: at line start
    out_lines = []
    for line in css.splitlines(keepends=True):
        new_line, c1 = LINE_LEFT_DECL.subn(r"\1inset-inline-start:", line)
        if c1:
            n += c1
            line = new_line
        new_line, c2 = LINE_RIGHT_DECL.subn(r"\1inset-inline-end:", line)
        if c2:
            n += c2
            line = new_line
        out_lines.append(line)
    return "".join(out_lines), n


def process_file(path: Path, dry: bool) -> int:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".vue":
        # Only touch <style> blocks
        total = 0
        def repl(m):
            nonlocal total
            opener, body, closer = m.group(1), m.group(2), m.group(3)
            new_body, n = process_css(body)
            total += n
            return opener + new_body + closer
        new_text = STYLE_BLOCK_RE.sub(repl, text)
    else:
        new_text, total = process_css(text)
    if total > 0 and new_text != text and not dry:
        path.write_text(new_text, encoding="utf-8", newline="\n")
    return total


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    files = [ROOT / f for f in (args or PRIORITY_FILES)]
    total = 0
    for f in files:
        if not f.exists():
            print(f"  SKIP missing : {f}")
            continue
        n = process_file(f, dry)
        if n:
            rel = f.relative_to(ROOT)
            print(f"  {n:3d}  {rel}")
            total += n
    label = "[dry-run] would change" if dry else "changed"
    print(f"\n{label} {total} occurrences across {len(files)} files")


if __name__ == "__main__":
    main()
