"""
voice_lines.py - Find the spoken lines in story.json passages and attach them as "voice" blocks.

Called by twine_to_json.py on every conversion. It:
  1. Finds speech in each run of text (italic quoted spans, or plain "quotes" as a fallback).
  2. Works out who is speaking (rules below), so each line can be voiced by the right voice.
  3. Gives every line a stable ID: <passage-slug>_<hash of speaker+text>. If the professor edits a
     line in Twine its ID changes, so only that line is regenerated.
  4. Inserts {"type":"voice","lines":[...]} before the text, so the game plays a line only when
     the branch containing it is shown.
  5. Writes voice/lines.json (all lines) and voice/script.csv (for reviewing who says what).

Speaker rules, checked in order for each paragraph:
  - The paragraph starts with "Man:" or "Harold:".
  - Otherwise, the first of "the man" / "he" / "Harold" in the words outside the quotes.
  - Otherwise, the opposite of the previous speaker (turn-taking). Harold if no one spoke yet.
Mistakes are fixed in voice/line_overrides.json, keyed by line ID.

Draft extra lines (voice/extra_lines.json) add audio that the Twine has no text for, e.g. Harold's
actual reply in each accent. They are marked as drafts for the professor to approve.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOICE_DIR = ROOT / "voice"
OVERRIDES_PATH = VOICE_DIR / "line_overrides.json"
EXTRA_PATH = VOICE_DIR / "extra_lines.json"

# Passages that are menus, credits or the end screen, not conversation: never voiced.
SKIP_PASSAGES = {"Start", "Field Journal", "Credits", "What is linguistics", "owlish interrogator",
                 "Global Navigation Footer", "StoryInit"}

SPEAKER_WORDS = re.compile(r"\b(the man|man:|harold:|harold|he)\b", re.I)
ITALIC = re.compile(r"\[i\](.*?)\[/i\]", re.S)
PLAIN_QUOTE = re.compile(r'"([^"]+)"')
BBCODE = re.compile(r"\[/?[a-z]+(=[^\]]*)?\]", re.I)
PLACEHOLDER = re.compile(r"\{\w+\}")


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:40]


def line_id(passage: str, speaker: str, text: str) -> str:
    digest = hashlib.sha1(f"{speaker}|{text}".encode("utf-8")).hexdigest()[:8]
    return f"{slug(passage)}_{digest}"


def plain(bbcode: str) -> str:
    return re.sub(r"\s+", " ", BBCODE.sub("", bbcode)).strip()


def strip_quotes(s: str) -> str:
    s = s.strip()
    s = re.sub(r'^"', "", s)
    s = re.sub(r'"[,.]?$', "", s)
    return s.strip().rstrip(",")


def _speaker_from_context(paragraph_plain: str, quotes: list[str]) -> str | None:
    outside = paragraph_plain
    for q in quotes:
        outside = outside.replace(q, " ")
    head = paragraph_plain.lstrip().lower()
    if head.startswith("man:"):
        return "man"
    if head.startswith("harold:"):
        return "harold"
    m = SPEAKER_WORDS.search(outside)
    if not m:
        return None
    word = m.group(1).lower()
    return "harold" if word.startswith("harold") else "man"


def extract(run_bbcode: str, passage: str, last_speaker: str | None) -> tuple[list[dict], str | None]:
    """Speech lines in one run of text. Returns (lines, last speaker)."""
    lines = []
    for para in re.split(r"\n\s*\n", run_bbcode):
        quotes_raw = []
        for m in ITALIC.finditer(para):
            inner = m.group(1)
            before = para[max(0, m.start() - 1) : m.start()]
            if inner.lstrip().startswith('"') or before == '"':
                quotes_raw.append(inner)
        if not quotes_raw and "[i]" not in para:
            quotes_raw = [f'"{q}"' for q in PLAIN_QUOTE.findall(plain(para))]
        if not quotes_raw:
            continue
        para_plain = plain(para)
        quote_plain = [plain(q) for q in quotes_raw]
        speaker = _speaker_from_context(para_plain, quote_plain)
        if speaker is None:
            speaker = {"man": "harold", "harold": "man"}.get(last_speaker or "", "harold")
        for q in quote_plain:
            text = strip_quotes(q)
            if not text or PLACEHOLDER.search(text):
                continue
            lines.append({"id": line_id(passage, speaker, text), "speaker": speaker, "text": text})
        last_speaker = speaker
    return lines, last_speaker


def annotate(blocks: list[dict], passage: str, last: str | None = None) -> tuple[list[dict], str | None]:
    """Insert voice blocks before each run of text/reveal blocks, recursing into branches."""
    out: list[dict] = []
    run: list[dict] = []

    def flush():
        nonlocal run, last
        if not run:
            return
        joined = "".join(b["text"] if b["type"] == "text" else b.get("label", "") for b in run)
        lines, last = extract(joined, passage, last)
        if lines:
            out.append({"type": "voice", "lines": lines})
        out.extend(run)
        run = []

    for b in blocks:
        if b["type"] in ("text", "reveal"):
            run.append(b)
            continue
        flush()
        if b["type"] == "if":
            b["then"], _ = annotate(b["then"], passage, last)
            b["else"], _ = annotate(b.get("else", []), passage, last)
        elif b["type"] == "style":
            b["content"], _ = annotate(b["content"], passage, None)
        out.append(b)
    flush()
    return out, last


def _load(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def process(story: dict) -> list[dict]:
    """Annotate every passage in place. Returns the full line list."""
    overrides = _load(OVERRIDES_PATH, {})
    extras = _load(EXTRA_PATH, {"lines": []})

    for name, entry in story["passages"].items():
        if name not in SKIP_PASSAGES:
            entry["blocks"], _ = annotate(entry["blocks"], name)

    # Draft extra lines: prepend to their passage
    for extra in extras.get("lines", []):
        p = story["passages"].get(extra["passage"])
        if p is None:
            print(f"WARNING: extra line for missing passage {extra['passage']!r}")
            continue
        line = {
            "id": line_id(extra["passage"], extra["speaker"], extra["text"]),
            "speaker": extra["speaker"],
            "text": extra["text"],
            "draft": True,
        }
        p["blocks"].insert(0, {"type": "voice", "lines": [line]})

    all_lines: list[dict] = []
    for name, entry in story["passages"].items():
        for vb in _collect_voice(entry["blocks"]):
            for line in vb["lines"]:
                ov = overrides.get(line["id"], {})
                if "speaker" in ov:
                    line["speaker"] = ov["speaker"]
                if ov.get("skip"):
                    line["skip"] = True
                if "tts_text" in ov:
                    line["tts_text"] = ov["tts_text"]
                all_lines.append({"passage": name, **line})
    return all_lines


def _collect_voice(blocks: list[dict]) -> list[dict]:
    found = []
    for b in blocks:
        if b["type"] == "voice":
            found.append(b)
        for key in ("then", "else", "content"):
            if key in b:
                found.extend(_collect_voice(b[key]))
    return found


def write_outputs(lines: list[dict]) -> None:
    seen: set[str] = set()
    lines = [l for l in lines if not (l["id"] in seen or seen.add(l["id"]))]
    VOICE_DIR.mkdir(exist_ok=True)
    (VOICE_DIR / "lines.json").write_text(json.dumps(lines, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with open(VOICE_DIR / "script.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "passage", "speaker", "text", "tts_text", "draft", "skip"])
        for l in lines:
            w.writerow([l["id"], l["passage"], l["speaker"], l["text"], l.get("tts_text", ""), "yes" if l.get("draft") else "", "yes" if l.get("skip") else ""])
    speakers: dict[str, int] = {}
    for l in lines:
        speakers[l["speaker"]] = speakers.get(l["speaker"], 0) + 1
    print(f"Voice: {len(lines)} lines -> voice/lines.json, voice/script.csv  {speakers}")
