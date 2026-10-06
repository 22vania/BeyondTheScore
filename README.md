# Vanilla Music

Vanilla Music is a local web application for practicing a piano score by ear. A player can listen to the right hand, the left hand, or both hands; choose an exact range of measures; slow down or speed up playback; and change the balance between the hands. The goal is to make a written score easier to study one passage at a time.

The current prototype uses a 24-measure piano piece labeled **Allegretto**. Its source was a scanned image of sheet music. We used the open-source [Audiveris optical music recognition (OMR) project](https://github.com/Audiveris/audiveris) to convert that image into the MusicXML file used by the app. Audiveris is part of the score-preparation workflow; it does not need to run when someone uses the website.

## What the website does

1. **Choose a hand.** Play the right-hand staff, the left-hand staff, or both together.
2. **Choose measures.** Enter a start and end measure, inclusive. For example, `8` through `20` plays from the beginning of measure 8 to the end of measure 20. Enter `1` through `24` for the whole written score. Invalid ranges display an error.
3. **Set speed.** Drag the speed slider from 0.5× to 2×. Its default is 1×.
4. **Play and repeat.** **Play selection** renders the current hand, measure range, and speed into an audio file. The page shows “Processing…” while rendering and then displays the audio player. **Repeat** renders the current selection again. The audio player can also be paused and replayed.
5. **Balance the hands.** The sliders below the audio player set right- and left-hand volume independently from 0% to 200%, with 100% as the default. Moving a slider remixes the most recently rendered passage; 0% mutes that hand. These sliders can also be adjusted with keyboard arrow keys when focused.

The app keeps the two hand tracks separate so a player can hear one hand clearly or compare how the hands fit together. A new **Play selection** click reads the inputs as they are at that moment, allowing the user to move from one passage to another without reloading the page.

## How it works

```text
Scanned score image
        │
        ▼
Audiveris OMR → MusicXML (.mxl)
                      │
                      ▼
                music21 reads the score
                      │
                      ▼
             Select hand(s) and measures
                      │
                      ▼
               Export each hand as MIDI
                      │
                      ▼
       FluidSynth + General MIDI SoundFont
                      │
                      ▼
          Mix hand volumes → WAV audio
                      │
                      ▼
                 Gradio audio player
```

`music21` identifies the two piano staves and extracts the requested measures. The app removes repeat-navigation marks from the *playback copy* of the selected passage, so the requested measures play once in written order. This matters when a selection includes only one side of a repeat sign. The original MusicXML file is not changed. The default tempo is 108 beats per minute because the OMR output did not preserve a tempo marking.

## Technology

| Tool | Role |
| --- | --- |
| Python | Application and audio-processing code |
| [Gradio](https://www.gradio.app/) | Local web interface and audio player |
| [music21](https://www.music21.org/music21docs/) | Read MusicXML, select staves and measures, and write MIDI |
| [FluidSynth](https://github.com/FluidSynth/fluidsynth) | Render MIDI into WAV audio |
| [GeneralUser GS SoundFont](https://github.com/mrbumpy409/GeneralUser-GS) | General MIDI instrument samples used for playback |
| NumPy | Mix the independently rendered hand tracks and apply volume levels |
| [Audiveris](https://github.com/Audiveris/audiveris) | Convert the original scanned score image to MusicXML before runtime |
| Jupyter notebook / IPython | Early score inspection and playback experiments |

## Project files

```text
Vanilla_Music/
├── gradio_app.py                  # Current website and audio-rendering logic
├── allegretto_audiveris.mxl      # Audiveris MusicXML output used by the app
├── Lesson 1 Score Parsing.ipynb  # Score exploration and prototype exercises
├── requirements.txt              # Python dependencies
├── tools/
│   ├── GeneralUser-GS.sf2        # General MIDI SoundFont
│   └── fluidsynth-.../bin/       # Local Windows FluidSynth executable
├── app.py                        # Earlier Flask prototype
├── src/                          # Earlier HTML/CSS/JavaScript prototype
└── .venv/                        # Local Python virtual environment
```

The Gradio app is the current website. `app.py` and `src/` are retained as earlier prototypes; they are not required to start the current interface.

## Run locally on Windows

From PowerShell in this folder:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe gradio_app.py
```

Then open [http://127.0.0.1:7860](http://127.0.0.1:7860) in a browser. Leave the PowerShell process running while using the website. The project currently expects FluidSynth and the `.sf2` SoundFont in `tools/`; these are separate from the Python packages in `requirements.txt`.

## Current scope and lessons learned

This is a local prototype built around one prepared MusicXML score. It does not currently accept score uploads, speech commands, or spoken note names. The notebook explores note names and arpeggios, but those experiments are not controls in the current website.

OMR is useful, but the transcription still needs human review. The notebook records that Audiveris missed the original title and tempo marking and that the score lacks a key-signature tag. The app supplies the working title and a default tempo for playback. A next step would be to compare the MusicXML against the original scan measure by measure and correct any notes that were misread. Another would be to let users upload their own MusicXML scores.
