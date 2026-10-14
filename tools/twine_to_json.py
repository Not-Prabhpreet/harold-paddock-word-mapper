#!/usr/bin/env python3
"""
twine_to_json.py - Convert a Twine 2 / Harlowe 3 story (published HTML) into the
structured dialogue graph the Godot game loads (dialogue/story.json).

Usage:
    python tools/twine_to_json.py "reference/Harold Paddock.html" dialogue/story.json

Re-run this whenever the professor exports a new version of the Twine story.

Supported Harlowe subset (everything the prototype uses):
    (set: $var to value)                 -> {"type":"set", ...}
    (if: cond)[hook] / (else:)[hook]     -> {"type":"if", "cond":..., "then":[...], "else":[...]}
    (go-to: "Passage")                   -> {"type":"goto", "target":...}
    (link-goto: "Text", "Passage")       -> {"type":"choice", ...}
    (prompt: "Question", "default")      -> {"type":"prompt", ...}
    (current-date:)                      -> "{current_date}" placeholder in text
    [[Text|Target]] / [[Target]] / ->/<- -> {"type":"choice", ...}
    [text]<name| ... (click-append: ?name)[more]  -> {"type":"reveal", ...}  (inline footnote)
    (align:...)+(box:...)[hook]          -> {"type":"style", "style":"centered", ...}
    {collapsed whitespace}               -> braces removed, inner content parsed
    //italic//, **bold**, <center>, <b>, <p>, <img>, <a href> -> BBCode / image blocks
    $var in prose                        -> "{var}" placeholder (interpolated at runtime)

Anything unrecognised is kept as plain text and reported as a warning so nothing is lost silently.
"""
import html
import json
import re
import sys
from pathlib import Path

WARNINGS: list[str] = []


def warn(msg: str) -> None:
    WARNINGS.append(msg)


# --------------------------------------------------------------------------- #
# 1. Pull passages out of the published HTML
# --------------------------------------------------------------------------- #
def load_passages(path: Path) -> tuple[dict, list[dict]]:
    src = path.read_text(encoding="utf-8")
    m = re.search(r"<tw-storydata([^>]*)>(.*?)</tw-storydata>", src, re.S)
    if not m:
        sys.exit("No <tw-storydata> found - is this a published Twine 2 HTML file?")
    attrs, body = m.group(1), m.group(2)

    def attr(name: str, s: str = attrs) -> str:
        mm = re.search(rf'{name}="([^"]*)"', s)
        return html.unescape(mm.group(1)) if mm else ""

    meta = {
        "title": attr("name"),
        "format": f'{attr("format")} {attr("format-version")}',
        "ifid": attr("ifid"),
        "startnode": int(attr("startnode") or 1),
    }
    passages = []
    for pattrs, text in re.findall(r"<tw-passagedata([^>]*)>(.*?)</tw-passagedata>", body, re.S):
        passages.append(
            {
                "pid": int(attr("pid", pattrs)),
                "name": attr("name", pattrs),
                "tags": [t for t in attr("tags", pattrs).split() if t],
                "source": html.unescape(text),
            }
        )
    return meta, passages


# --------------------------------------------------------------------------- #
# 2. Small balanced-delimiter helpers
# --------------------------------------------------------------------------- #
def match_close(s: str, i: int, open_ch: str, close_ch: str) -> int:
    """s[i] == open_ch; return index of the matching close_ch. Treats [[...]] links as atomic."""
    depth = 0
    j = i
    while j < len(s):
        if s.startswith("[[", j) and open_ch == "[" and j != i:
            k = s.find("]]", j + 2)
            if k == -1:
                break
            j = k + 2
            continue
        c = s[j]
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError(f"Unbalanced {open_ch}{close_ch} starting at {i}: {s[i:i+40]!r}")


def parse_value(raw: str):
    raw = raw.strip()
    if raw == "true":
        return True
    if raw == "false":
        return False
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    if re.fullmatch(r"-?\d+\.\d+", raw):
        return float(raw)
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    if raw.startswith("$"):
        return {"var": raw[1:]}
    warn(f"Unrecognised value literal {raw!r}; kept as string")
    return raw


def parse_condition(raw: str) -> dict:
    """'$a is true and $b contains "x"' -> {"all":[{var,op,value},...]}"""
    clauses = []
    for part in re.split(r"\s+and\s+", raw.strip()):
        mm = re.fullmatch(r"\$(\w+)\s+(is not|is|contains)\s+(.+)", part.strip())
        if not mm:
            warn(f"Unparsed condition clause {part!r}")
            clauses.append({"raw": part})
            continue
        var, op, val = mm.groups()
        clauses.append({"var": var, "op": op.replace(" ", "_"), "value": parse_value(val)})
    return {"all": clauses}


def split_args(raw: str) -> list[str]:
    """Split macro args on top-level commas (respecting quotes/parens)."""
    out, depth, quote, cur = [], 0, None, ""
    for c in raw:
        if quote:
            cur += c
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
            cur += c
        elif c == "(":
            depth += 1
            cur += c
        elif c == ")":
            depth -= 1
            cur += c
        elif c == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += c
    if cur.strip():
        out.append(cur)
    return [a.strip() for a in out]


# --------------------------------------------------------------------------- #
# 3. Prose -> BBCode (what Godot's RichTextLabel renders)
# --------------------------------------------------------------------------- #
def strip_notes(s: str) -> tuple[str, list[str]]:
    notes = [n.strip() for n in re.findall(r"<!--(.*?)-->", s, re.S)]
    return re.sub(r"<!--.*?-->", "", s, flags=re.S), notes


def pre_markup(s: str) -> str:
    """Convert Harlowe //italic// and **bold** BEFORE structural parsing, because a span can
    straddle an inline hook (e.g. Man: //"'dat [one]<insect|? You kiddin' me?"//).
    Uses \x02 \x03 as temporary stand-ins for [ ] so the bracket matcher ignores them."""
    s = re.sub(r"(?<!:)//(.+?)(?<!:)//", "\x02i\x03\\1\x02/i\x03", s, flags=re.S)  # (?<!:) skips http://
    s = re.sub(r"\*\*(.+?)\*\*", "\x02b\x03\\1\x02/b\x03", s, flags=re.S)
    return s


def prose_to_bbcode(s: str) -> str:
    s = s.replace("\\\n", "")  # Harlowe line-continuation backslash
    s = s.replace("&nbsp;", " ")
    s = s.replace("\x02", "[").replace("\x03", "]")
    # Harlowe column layout markers (|==|, |=, =|) are pure layout -> drop
    s = re.sub(r"^\s*(\|==\||\|=|=\|)\s*$", "", s, flags=re.M)
    s = re.sub(r"(?m)^---\s*$", "[center]~ ~ ~[/center]", s)
    s = re.sub(r"<center>(.*?)</center>", r"[center]\1[/center]", s, flags=re.S | re.I)
    s = re.sub(r"<b>(.*?)</b>", r"[b]\1[/b]", s, flags=re.S | re.I)
    s = re.sub(r"<b>", "[b]", s, flags=re.I)  # Credits has an unclosed <b>
    s = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"[url=\1]\2[/url]", s, flags=re.S | re.I)
    s = re.sub(r"<p[^>]*>", "\n\n", s, flags=re.I)
    s = re.sub(r"</p>", "", s, flags=re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</?div[^>]*>", "", s, flags=re.I)
    s = re.sub(r"<img [^>]*presskit/icons[^>]*>(</img>)?", "", s, flags=re.I)  # CC badge icons
    s = s.replace("(current-date:)", "{current_date}")
    s = re.sub(r"\$(\w+)", r"{\1}", s)
    return s


def tidy_text(s: str) -> str:
    """Normalise whitespace but KEEP paragraph breaks: text blocks are concatenated verbatim
    by the game, so a block that is only '\n\n' is what separates two paragraphs."""
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    if not s.strip():
        return "\n\n" if s.count("\n") >= 2 else ("\n" if "\n" in s else " ")
    return s


# --------------------------------------------------------------------------- #
# 4. Harlowe source -> ordered list of blocks
# --------------------------------------------------------------------------- #
MACRO_RE = re.compile(r"\((?P<name>[a-z\-]+):")
NAMED_HOOK_RE = re.compile(r"\[(?P<label>[^\[\]]*)\]<(?P<id>\w+)\|")


class Parser:
    def __init__(self, passage_names: set[str]):
        self.passage_names = passage_names

    # -- entry ----------------------------------------------------------------
    def parse(self, src: str) -> list[dict]:
        blocks = self._parse_seq(src)
        return self._post(blocks)

    # -- main loop ------------------------------------------------------------
    def _parse_seq(self, s: str) -> list[dict]:
        blocks: list[dict] = []
        buf = ""
        i = 0

        def flush():
            nonlocal buf
            if buf:
                self._push_text(blocks, buf)
                buf = ""

        while i < len(s):
            # [[link]]
            if s.startswith("[[", i):
                j = s.find("]]", i)
                flush()
                blocks.append(self._parse_link(s[i + 2 : j]))
                i = j + 2
                continue
            # {collapse whitespace}
            if s[i] == "{":
                j = match_close(s, i, "{", "}")
                flush()
                blocks.extend(self._parse_seq(s[i + 1 : j]))
                i = j + 1
                continue
            # (current-date:) is inline prose, not structure
            if s.startswith("(current-date:)", i):
                buf += "{current_date}"
                i += len("(current-date:)")
                continue
            # (macro: ...)
            m = MACRO_RE.match(s, i)
            if m:
                j = match_close(s, i, "(", ")")
                name = m.group("name")
                args = s[m.end() : j]
                i = j + 1
                # changer chains: (align:)+(box:)[hook]
                while re.match(r"\s*\+\s*\(", s[i:]):
                    k = s.index("(", i)
                    j2 = match_close(s, k, "(", ")")
                    i = j2 + 1
                hook = None
                hm = re.match(r"\s*\[", s[i:])
                if hm and name in ("if", "else", "else-if", "unless", "click-append", "align", "box", "link", "hidden"):
                    k = i + hm.end() - 1
                    if s.startswith("[[", k):
                        # (if: ...)[[Link]]  -> the changer is attached to a link, not a hook
                        j3 = s.find("]]", k) + 1
                        hook = s[k : j3 + 1]
                    else:
                        j3 = match_close(s, k, "[", "]")
                        hook = s[k + 1 : j3]
                    i = j3 + 1
                flush()
                blocks.extend(self._macro(name, args, hook))
                continue
            # [label]<id|  named hook (reveal anchor)
            nh = NAMED_HOOK_RE.match(s, i)
            if nh:
                flush()
                blocks.append({"type": "anchor", "id": nh.group("id"), "label": prose_to_bbcode(nh.group("label"))})
                i = nh.end()
                continue
            # <img ...>
            im = re.match(r'<img\s[^>]*src="([^"]+)"[^>]*>(</img>)?', s[i:])
            if im:
                flush()
                blocks.append({"type": "image", "src": im.group(1)})
                i += im.end()
                continue
            # bare [hook] (e.g. the poem) -> parse inside
            if s[i] == "[":
                j = match_close(s, i, "[", "]")
                flush()
                blocks.extend(self._parse_seq(s[i + 1 : j]))
                i = j + 1
                continue
            buf += s[i]
            i += 1
        flush()
        return blocks

    def _push_text(self, blocks: list[dict], raw: str) -> None:
        txt = tidy_text(prose_to_bbcode(raw))
        if blocks and blocks[-1]["type"] == "text":
            blocks[-1]["text"] = tidy_text(blocks[-1]["text"] + txt)
        else:
            blocks.append({"type": "text", "text": txt})

    # -- pieces ---------------------------------------------------------------
    def _parse_link(self, inner: str) -> dict:
        if "|" in inner:
            text, target = inner.split("|", 1)
        elif "->" in inner:
            text, target = inner.split("->", 1)
        elif "<-" in inner:
            target, text = inner.split("<-", 1)
        else:
            text = target = inner
        text, target = text.strip(), target.strip()
        if target not in self.passage_names:
            warn(f"Link to missing passage {target!r}")
        return {"type": "choice", "text": text, "target": target}

    def _macro(self, name: str, args: str, hook: str | None) -> list[dict]:
        if name == "set":
            mm = re.fullmatch(r"\s*\$(\w+)\s+to\s+(.+)", args, re.S)
            if not mm:
                warn(f"Unparsed (set:) {args!r}")
                return [{"type": "raw", "macro": name, "args": args}]
            var, val = mm.groups()
            val = val.strip()
            pm = re.fullmatch(r"\(prompt:(.*)\)", val, re.S)
            if pm:
                a = [parse_value(x) for x in split_args(pm.group(1))]
                return [{"type": "prompt", "var": var, "text": a[0], "default": a[1] if len(a) > 1 else ""}]
            return [{"type": "set", "var": var, "value": parse_value(val)}]
        if name in ("if", "unless"):
            cond = parse_condition(args)
            if name == "unless":
                cond = {"not": cond}
            return [{"type": "if", "cond": cond, "then": self._parse_seq(hook or ""), "else": []}]
        if name == "else-if":
            return [{"type": "else-if", "cond": parse_condition(args), "then": self._parse_seq(hook or "")}]
        if name == "else":
            return [{"type": "else", "then": self._parse_seq(hook or "")}]
        if name == "go-to":
            (target,) = [parse_value(x) for x in split_args(args)]
            if target not in self.passage_names:
                warn(f"(go-to:) missing passage {target!r}")
            return [{"type": "goto", "target": target}]
        if name == "link-goto":
            a = [parse_value(x) for x in split_args(args)]
            target = a[1] if len(a) > 1 else a[0]
            if target not in self.passage_names:
                warn(f"(link-goto:) missing passage {target!r}")
            return [{"type": "choice", "text": a[0], "target": target}]
        if name == "click-append":
            hid = args.strip().lstrip("?")
            return [{"type": "reveal", "id": hid, "content": self._parse_seq(hook or "")}]
        if name in ("align", "box"):
            return [{"type": "style", "style": "centered", "content": self._parse_seq(hook or "")}]
        if name == "current-date":
            return [{"type": "text", "text": "{current_date}"}]
        warn(f"Unknown macro ({name}:) kept raw")
        return [{"type": "raw", "macro": name, "args": args, "hook": hook}]

    # -- post-processing: attach else/else-if, merge anchor + reveal ------------
    def _post(self, blocks: list[dict]) -> list[dict]:
        out: list[dict] = []
        for b in blocks:
            if b["type"] in ("else", "else-if"):
                prev = next((x for x in reversed(out) if x["type"] != "text" or x["text"].strip()), None)
                if prev is None or prev["type"] != "if":
                    warn(f"({b['type']}:) without preceding (if:)")
                    out.append(b)
                    continue
                if b["type"] == "else":
                    prev["else"] = self._post(b["then"])
                else:
                    prev["else"] = [{"type": "if", "cond": b["cond"], "then": self._post(b["then"]), "else": []}]
                continue
            if b["type"] == "if":
                b["then"] = self._post(b["then"])
                b["else"] = self._post(b["else"])
            if b["type"] in ("reveal", "style"):
                b["content"] = self._post(b["content"])
            out.append(b)
        # merge [label]<id| anchors with their (click-append: ?id) reveal
        merged: list[dict] = []
        for b in out:
            if b["type"] == "anchor":
                merged.append({"type": "reveal", "id": b["id"], "label": b["label"], "content": []})
            elif b["type"] == "reveal":
                tgt = next((x for x in merged if x["type"] == "reveal" and x["id"] == b["id"]), None)
                if tgt is None:
                    warn(f"(click-append: ?{b['id']}) without anchor hook")
                    merged.append(b)
                else:
                    tgt["content"] = b["content"]
            else:
                merged.append(b)
        return merged


# --------------------------------------------------------------------------- #
# 5. Assemble story.json
# --------------------------------------------------------------------------- #
def collect(blocks: list[dict], kind: str) -> list[dict]:
    found = []
    for b in blocks:
        if b["type"] == kind:
            found.append(b)
        for key in ("then", "else", "content"):
            if key in b:
                found.extend(collect(b[key], kind))
    return found


def main(src: str, dst: str) -> None:
    meta, passages = load_passages(Path(src))
    names = {p["name"] for p in passages}
    parser = Parser(names)

    story: dict = {
        "title": meta["title"],
        "source_format": meta["format"],
        "ifid": meta["ifid"],
        "start": next(p["name"] for p in passages if p["pid"] == meta["startnode"]),
        "variables": {},
        "passages": {},
    }

    for p in passages:
        text, notes = strip_notes(p["source"])
        blocks = parser.parse(pre_markup(text))
        # trim leading/trailing whitespace of the passage as a whole
        texts = [b for b in blocks if b["type"] == "text"]
        if texts:
            texts[0]["text"] = texts[0]["text"].lstrip()
            texts[-1]["text"] = texts[-1]["text"].rstrip()
        blocks = [b for b in blocks if not (b["type"] == "text" and b["text"] == "")]
        entry = {
            "pid": p["pid"],
            "tags": p["tags"],
            "blocks": blocks,
            "links": sorted({c["target"] for c in collect(blocks, "choice")} | {g["target"] for g in collect(blocks, "goto")}),
            "sets": [{"var": s["var"], "value": s["value"]} for s in collect(blocks, "set")],
            "reads": sorted({c["var"] for i in collect(blocks, "if") for c in i["cond"].get("all", []) if "var" in c}),
        }
        if notes:
            entry["author_notes"] = notes
        story["passages"][p["name"]] = entry

    # StoryInit is Harlowe's special "runs once before Start" passage -> initial variable values
    init = story["passages"].get("StoryInit")
    if init:
        for s in init["sets"]:
            story["variables"][s["var"]] = s["value"]
    story["variables"].setdefault("name", "")

    # Convenience: which passages are reachable from start
    seen, stack = set(), [story["start"]]
    while stack:
        n = stack.pop()
        if n in seen or n not in story["passages"]:
            continue
        seen.add(n)
        stack.extend(story["passages"][n]["links"])
    story["unreachable"] = sorted(set(story["passages"]) - seen)

    # Spoken lines for voice acting (see tools/voice_lines.py)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import voice_lines

    voice_lines.write_outputs(voice_lines.process(story))

    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Path(dst).write_text(json.dumps(story, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {dst}: {len(story['passages'])} passages, start={story['start']!r}")
    print(f"Variables: {story['variables']}")
    print(f"Unreachable from start: {story['unreachable']}")
    for w in WARNINGS:
        print("WARNING:", w)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
