# Harold Paddock: Word Mapper

A 3D game about doing dialect fieldwork in Newfoundland, made for **Linguistics 2210: Language in
Newfoundland and Labrador** at Memorial University. It's the first episode of a planned series
called *Something's Fishy in Carbonear*, and it's built on Dr. Paul De Decker's original Twine
prototype of the same story.

You play as a young Harold Paddock in the summer of 1964, cycling into Carbonear on his first day
of fieldwork. You meet an older man working in his garden, decide how Harold should talk to him,
decide whether to ask for informed consent before asking survey questions, and find out what he
calls a dragonfly. Whether that answer ends up in Harold's field journal is up to you.

The game is meant to give students a feel for a few things from the course:

- **Style-shifting.** Harold can answer the man's "'ow's she gon', by" in a local accent, in his
  own Long Branch vernacular, or in a St. John's standard accent, and the man reacts differently
  to each.
- **Research ethics.** You can ask a survey question with proper informed consent, or just chat
  about the weather.
- **Lexical variation.** The dragonfly question gets you "'orse-stinger".
- **Recording your data.** If you don't write the finding down, it's gone.

The end screen gives feedback based on the choices you made.

## Running the game

You only need Godot. Everything else (models, textures, the story) is already in the repo.

1. Download **Godot 4.7** from https://godotengine.org/download. The standard build is fine, you
   don't need the .NET one. It's a single program, so there's nothing to install.
2. Open Godot, click **Import**, and choose the `project.godot` file in this folder.
3. Press **F5**, or the play button in the top right.

The first time you open the project, Godot spends a minute importing the models and images. That
only happens once.

### Controls

| Key | Does |
|---|---|
| W A S D | Walk |
| Shift | Run |
| Mouse | Turn the camera |
| E | Talk to someone nearby |
| 1 to 9, or click | Pick a choice |
| J | Open Harold's field journal |
| Esc | Free the mouse (click to grab it again) |
| F3 | Show the story variables, which is handy for checking the branches |

### A quick walkthrough

The game opens on a title screen, asks for your name, and then shows the 1964 introduction from
the Twine. The underlined words in the text are footnotes you can click. Choose "Continue down the
highway" to drop into Carbonear. The man is by the potato garden to the right of the house. Walk
up to him and he'll wave, then press E to talk.

## How the project is put together

```
reference/        Dr. De Decker's Twine prototype (the source for the whole story)
dialogue/         the story converted to JSON, plus presentation.json (how each passage is staged)
scenes/           Godot scenes: Carbonear, the player, the NPC, the UI screens
scripts/          the game code (GDScript)
assets/           models, concept art, UI art, images and shaders
tools/            Python scripts for converting the Twine and generating voices
tools/blender/    Python scripts that build every 3D model in Blender
voice/            the spoken lines and voice settings (no audio yet)
data/             quotativesdata.csv, the sample data the future ledger will match
tests/            automated tests
```

### The story comes straight from the Twine

The dialogue isn't typed into the game by hand. `tools/twine_to_json.py` reads the Twine file and
turns it into `dialogue/story.json`, which the game plays. The wording, the branching and the
variables (`$name`, `$accent`, `$ethics`, `$lexicon`, `$question`) all carry over exactly as they
are in the Twine. So if the story changes in Twine, you publish it to
`reference/Harold Paddock.html` and run:

```
python tools/twine_to_json.py "reference/Harold Paddock.html" dialogue/story.json
```

The next time the game runs, it uses the new version. This needs Python 3 and nothing else.

`dialogue/presentation.json` covers the parts the Twine doesn't, like which passages show up as
full journal pages, when the dragonfly flies past, and which portrait shows for each speaker.

### The 3D models

Every model was built in Blender from the concept art in `assets/`, using the scripts in
`tools/blender/`. You don't need Blender to play, because the finished `.glb` files are already
here. If you want to change a model, install Blender 5.2, edit its script and run it, for example:

```
blender -b -P tools/blender/characters.py -- garden_man
blender -b -P tools/blender/characters.py -- harold
blender -b -P tools/blender/saltbox_house.py
blender -b -P tools/blender/props.py -- bicycle
```

`props.py` also builds `dragonfly`, `picket_fence`, `potato_patch`, `spruce_tree`, `route_sign`,
`grass_tuft` and `beach_rock`. Each run saves preview images next to the model, so you can check
it before opening the game.

### Tests

There are three automated tests that play through the game without opening a window. Run them
from this folder using the console version of Godot that comes in the same download:

```
Godot_v4.7.2-stable_win64_console.exe --headless --path . -s res://tests/test_dialogue.gd
Godot_v4.7.2-stable_win64_console.exe --headless --path . -s res://tests/test_episode.gd
Godot_v4.7.2-stable_win64_console.exe --headless --path . -s res://tests/test_assets.gd
```

Each one should finish with a line saying it passed. `test_dialogue` walks every branch of the
story, and `test_episode` plays the whole episode in the 3D scene the way a student would.

## What's not done yet

- **Voices.** All 31 spoken lines are pulled out of the Twine and ready, and `tools/voices.py` can
  generate them with ElevenLabs once there's an API key (see `.env.example`). I'd like the voices
  checked by Newfoundland listeners before using them, since the accents are the whole point.
- **Harold's own replies.** The Twine never says what Harold actually says when he answers in
  each accent, so I wrote three short draft lines in `voice/extra_lines.json`. They're only
  there for the voice recordings and still need Dr. De Decker's approval.
- **Ambient sound,** like wind, gulls and waves.
- **The Fieldwork Ledger.** The plan is for each finding Harold records to become a row in the
  same format as `data/quotativesdata.csv`, so a playthrough produces real data that could be
  analysed later.

## Credits

Game design and story: Dr. Paul De Decker, from the original Twine prototype for Linguistics 2210.

Paddock, H. J. (1966). *A dialect survey of Carbonear, Newfoundland* (Doctoral dissertation,
Memorial University of Newfoundland).

Images from the prototype:

- "DRAGONFLY" by whologwhy, licensed under CC BY 2.0.
- The Route 70 sign is from Wikimedia Commons and is in the public domain.
- The MUN Digital Archives photo used for the "owlish interrogator" footnote still needs
  permission confirmed before any public release.

The concept art, title screen, portraits and illustrations were made with an AI image model and
then used as references for the Blender models. Full image sources are listed in
`assets/images/ATTRIBUTION.md`.
