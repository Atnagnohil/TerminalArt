"""ANSI 转义码 → HTML CSS span 转换器"""
import re

_FG_RE = re.compile(r'\033\[38;2;(\d+);(\d+);(\d+)m')
_BG_RE = re.compile(r'\033\[48;2;(\d+);(\d+);(\d+)m')
_RESET_RE = re.compile(r'\033\[0m')


def ansi_to_html(ansi_text: str) -> str:
    """将 ANSI 转义码文本转换为带 CSS 的 HTML"""

    lines = ansi_text.split('\n')
    html_lines = []

    for line in lines:
        html_line_parts = []
        pos = 0
        current_fg = None
        current_bg = None

        while pos < len(line):
            fg_match = _FG_RE.search(line, pos)
            bg_match = _BG_RE.search(line, pos)
            reset_match = _RESET_RE.search(line, pos)

            closest = None
            closest_type = None
            for m, t in [(fg_match, 'fg'), (bg_match, 'bg'), (reset_match, 'reset')]:
                if m and (closest is None or m.start() < closest.start()):
                    closest = m
                    closest_type = t

            if closest is None:
                text = line[pos:]
                if text:
                    html_line_parts.append(
                        _wrap_span(text, current_fg, current_bg))
                break

            if closest.start() > pos:
                text = line[pos:closest.start()]
                if text:
                    html_line_parts.append(
                        _wrap_span(text, current_fg, current_bg))

            if closest_type == 'fg':
                current_fg = (int(closest.group(1)),
                              int(closest.group(2)),
                              int(closest.group(3)))
            elif closest_type == 'bg':
                current_bg = (int(closest.group(1)),
                              int(closest.group(2)),
                              int(closest.group(3)))
            elif closest_type == 'reset':
                current_fg = None
                current_bg = None

            pos = closest.end()

        html_lines.append("".join(html_line_parts))

    body = "<br>".join(html_lines)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    background: #000;
    color: #fff;
    font-family: "Cascadia Mono", "SF Mono", "Consolas", "Courier New", monospace;
    font-size: 8px;
    line-height: 1.0;
    letter-spacing: 0;
    white-space: pre;
  }}
</style>
</head>
<body>{body}</body>
</html>"""


def _wrap_span(text: str, fg: tuple | None, bg: tuple | None) -> str:
    if not text:
        return ""
    styles = []
    if fg:
        styles.append(f"color:rgb({fg[0]},{fg[1]},{fg[2]})")
    if bg:
        styles.append(f"background:rgb({bg[0]},{bg[1]},{bg[2]})")
    if styles:
        return f'<span style="{";".join(styles)}">{_escape_html(text)}</span>'
    return _escape_html(text)


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
