"""The splitting rule `line-pack-v1` (research.md, section 12).

The rule uses lines and characters only, so the same text gives the same passages everywhere.
Whenever its output could change, the rule gets a new name.
"""

RULE = "line-pack-v1"
MAX_CHARS = 2000


def _lines_and_pieces(contents: str, max_chars: int) -> list[str]:
    """Steps 1 to 3: the non-empty lines, stripped, and a line longer than `max_chars` cut into
    pieces at the last whitespace within the limit, or after exactly `max_chars` characters."""
    units = []
    for line in contents.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = line.strip()
        start = 0
        while len(line) - start > max_chars:
            end = start + max_chars
            cut = next((at for at in range(end - 1, start, -1) if line[at].isspace()), None)
            if cut is None:
                units.append(line[start:end])
                start = end
            else:
                units.append(line[start:cut].rstrip())
                start = cut
            while line[start].isspace():
                start += 1
        if start < len(line):
            units.append(line[start:])
    return units


def split(contents: str, max_chars: int = MAX_CHARS) -> list[str]:
    """The passages of one article, in order; the passage at place `n` has `passage_no` `n`.

    Step 4: the lines and pieces are packed in order; the next one joins the current passage,
    after a line feed, when the passage stays within `max_chars` characters. Step 5: a text
    without a non-empty line gives no passage.
    """
    if max_chars < 1:
        raise ValueError("max_chars is at least 1")
    passages: list[str] = []
    for unit in _lines_and_pieces(contents, max_chars):
        if passages and len(passages[-1]) + 1 + len(unit) <= max_chars:
            passages[-1] += "\n" + unit
        else:
            passages.append(unit)
    return passages
