#!/usr/bin/env python3
"""
voices.py - Design character voices and generate every voiced line with ElevenLabs.

Setup: put ELEVENLABS_API_KEY=... in the project's .env file (see .env.example).

  python tools/voices.py design man          # 3 preview voices for "man" -> voice/previews/
  python tools/voices.py design harold_local # remix of harold's voice (same person, new accent):
                                             # pick a voice for harold first
  python tools/voices.py pick man 2          # keep preview 2: saves it to your ElevenLabs library
                                             # and writes its voice_id into voice/voices.json
  python tools/voices.py use man <voice_id>  # or use any existing voice from your library
  python tools/voices.py status              # which speakers have voices, how many lines are missing
  python tools/voices.py generate            # voice every missing line -> voice/audio/<id>.mp3
  python tools/voices.py generate --passage Reply --force   # redo one passage
  python tools/voices.py generate --dry-run  # show what would be sent and the character count

Lines come from voice/lines.json, written by tools/twine_to_json.py. Speakers and voice
descriptions live in voice/voices.json. A line is only generated if its audio file is missing,
so editing a line in Twine (which changes its ID) regenerates just that line.
"""
from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _api import ROOT, read_json, request, require_key, write_json  # noqa: E402

API = "https://api.elevenlabs.io/v1"
VOICE_DIR = ROOT / "voice"
CONFIG = VOICE_DIR / "voices.json"
LINES = VOICE_DIR / "lines.json"
AUDIO = VOICE_DIR / "audio"
PREVIEWS = VOICE_DIR / "previews"


def headers() -> dict:
    return {"xi-api-key": require_key("ELEVENLABS_API_KEY")}


def config() -> dict:
    cfg = read_json(CONFIG)
    if cfg is None:
        sys.exit(f"Missing {CONFIG}")
    return cfg


def speaker_cfg(cfg: dict, speaker: str) -> dict:
    sp = cfg["speakers"].get(speaker)
    if sp is None:
        sys.exit(f"Unknown speaker {speaker!r}. Known: {', '.join(cfg['speakers'])}")
    return sp


def cmd_design(args) -> None:
    cfg = config()
    sp = speaker_cfg(cfg, args.speaker)
    body = {
        "voice_description": sp["design"],
        "text": sp.get("design_sample") or None,
        "auto_generate_text": not sp.get("design_sample"),
    }
    base = sp.get("remix_of")
    if base:
        base_id = speaker_cfg(cfg, base).get("voice_id")
        if not base_id:
            sys.exit(f"'{args.speaker}' is a remix of '{base}'. Design and pick '{base}' first.")
        print(f"Remixing '{base}' into '{args.speaker}': {sp['design']}")
        url = f"{API}/text-to-voice/{base_id}/remix"
    else:
        body["model_id"] = cfg.get("design_model_id", "eleven_ttv_v3")
        print(f"Designing '{args.speaker}': {sp['design']}")
        url = f"{API}/text-to-voice/design"
    resp = request("POST", url, headers(), body, timeout=300)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    previews = resp.get("previews", [])
    store = read_json(PREVIEWS / "previews.json", {})
    store[args.speaker] = []
    for i, p in enumerate(previews, 1):
        path = PREVIEWS / f"{args.speaker}_{i}.mp3"
        path.write_bytes(base64.b64decode(p["audio_base_64"]))
        store[args.speaker].append(p["generated_voice_id"])
        print(f"  preview {i}: {path.relative_to(ROOT)}")
    write_json(PREVIEWS / "previews.json", store)
    print(f"Listen, then: python tools/voices.py pick {args.speaker} <1-{len(previews)}>")


def cmd_pick(args) -> None:
    cfg = config()
    sp = speaker_cfg(cfg, args.speaker)
    ids = read_json(PREVIEWS / "previews.json", {}).get(args.speaker, [])
    if not 1 <= args.number <= len(ids):
        sys.exit(f"No preview {args.number} for {args.speaker}; run design first.")
    body = {
        "voice_name": f"Word Mapper - {args.speaker}",
        "voice_description": sp["design"][:1000],
        "generated_voice_id": ids[args.number - 1],
    }
    resp = request("POST", f"{API}/text-to-voice", headers(), body)
    sp["voice_id"] = resp["voice_id"]
    write_json(CONFIG, cfg)
    print(f"'{args.speaker}' now uses voice {resp['voice_id']} (saved in voice/voices.json)")


def cmd_use(args) -> None:
    cfg = config()
    speaker_cfg(cfg, args.speaker)["voice_id"] = args.voice_id
    write_json(CONFIG, cfg)
    print(f"'{args.speaker}' now uses voice {args.voice_id}")


def pending(cfg: dict, args) -> list[dict]:
    lines = read_json(LINES, [])
    out = []
    for line in lines:
        if line.get("skip"):
            continue
        if getattr(args, "passage", None) and line["passage"] != args.passage:
            continue
        if getattr(args, "speaker", None) and line["speaker"] != args.speaker:
            continue
        if (AUDIO / f"{line['id']}.mp3").exists() and not getattr(args, "force", False):
            continue
        out.append(line)
    return out


def cmd_status(args) -> None:
    cfg = config()
    lines = [l for l in read_json(LINES, []) if not l.get("skip")]
    print(f"{len(lines)} voiced lines in voice/lines.json")
    for name, sp in cfg["speakers"].items():
        mine = [l for l in lines if l["speaker"] == name]
        done = sum((AUDIO / f"{l['id']}.mp3").exists() for l in mine)
        voice = sp.get("voice_id") or "NO VOICE YET (run design + pick)"
        print(f"  {name:14} {done}/{len(mine)} generated   voice: {voice}")
    unknown = {l["speaker"] for l in lines} - set(cfg["speakers"])
    if unknown:
        print(f"  Speakers missing from voices.json: {', '.join(sorted(unknown))}")


def cmd_generate(args) -> None:
    cfg = config()
    todo = pending(cfg, args)
    if not todo:
        print("Nothing to generate. Every line already has audio (use --force to redo).")
        return
    chars = sum(len(l.get("tts_text", l["text"])) for l in todo)
    print(f"{len(todo)} lines, {chars} characters")
    missing = sorted({l["speaker"] for l in todo if not cfg["speakers"].get(l["speaker"], {}).get("voice_id")})
    if missing and not args.dry_run:
        sys.exit(f"No voice_id yet for: {', '.join(missing)}. Run: python tools/voices.py design <speaker>")
    AUDIO.mkdir(parents=True, exist_ok=True)
    hdr = None if args.dry_run else headers()
    for line in todo:
        sp = cfg["speakers"][line["speaker"]]
        text = line.get("tts_text", line["text"])
        if args.dry_run:
            print(f"  [{line['speaker']}] {line['id']}: {text}")
            continue
        body = {
            "text": text,
            "model_id": sp.get("model_id", cfg.get("model_id", "eleven_v3")),
            "voice_settings": {**cfg.get("voice_settings", {}), **sp.get("voice_settings", {})},
        }
        url = f"{API}/text-to-speech/{sp['voice_id']}?output_format={cfg.get('output_format', 'mp3_44100_128')}"
        audio = request("POST", url, hdr, body, raw=True, timeout=300)
        (AUDIO / f"{line['id']}.mp3").write_bytes(audio)
        print(f"  ok [{line['speaker']}] {line['id']}")
    if not args.dry_run:
        print("Done. Godot imports the new files the next time the editor or a test runs.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("design"); p.add_argument("speaker"); p.set_defaults(fn=cmd_design)
    p = sub.add_parser("pick"); p.add_argument("speaker"); p.add_argument("number", type=int); p.set_defaults(fn=cmd_pick)
    p = sub.add_parser("use"); p.add_argument("speaker"); p.add_argument("voice_id"); p.set_defaults(fn=cmd_use)
    p = sub.add_parser("status"); p.set_defaults(fn=cmd_status)
    p = sub.add_parser("generate")
    p.add_argument("--passage"); p.add_argument("--speaker")
    p.add_argument("--force", action="store_true"); p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_generate)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
