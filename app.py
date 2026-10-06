from pathlib import Path
import copy
import os
import shutil
import subprocess
import tempfile

from flask import Flask, jsonify, request, send_from_directory, send_file
import music21 as m21

ROOT = Path(__file__).resolve().parent
SCORE_PATH = ROOT / "allegretto_audiveris.mxl"
STATIC = ROOT / "src"
app = Flask(__name__, static_folder=str(STATIC), static_url_path="")
score = m21.converter.parse(str(SCORE_PATH))


def hand_stream(hand):
    if hand == "both":
        return score
    suffix = "-Staff1" if hand == "right" else "-Staff2"
    for part in score.parts:
        if str(part.id).endswith(suffix):
            return part
    return score.parts[0] if hand == "right" else score.parts[-1]


def measure_count(stream):
    own = list(stream.getElementsByClass(m21.stream.Measure))
    if own:
        return len(own)
    return max((len(p.getElementsByClass(m21.stream.Measure)) for p in stream.parts), default=0)


def note_names(stream):
    result = []
    for element in stream.flatten().notesAndRests:
        if isinstance(element, m21.chord.Chord):
            result.append({"kind": "chord", "notes": [p.nameWithOctave for p in element.pitches]})
        elif isinstance(element, m21.note.Note):
            result.append({"kind": "note", "notes": [element.nameWithOctave]})
    return result


@app.get("/api/score")
def score_info():
    return jsonify({"title": "Allegretto", "measures": measure_count(score), "parts": [str(p.id) for p in score.parts]})


@app.post("/api/notes")
def notes():
    data = request.get_json(force=True)
    hand = data.get("hand", "right")
    start, end = int(data.get("start", 1)), int(data.get("end", measure_count(score)))
    stream = hand_stream(hand).measures(start, end)
    return jsonify({"events": note_names(stream)})


@app.post("/api/render")
def render():
    data = request.get_json(force=True)
    hand = data.get("hand", "right")
    start, end = int(data.get("start", 1)), int(data.get("end", measure_count(score)))
    speed = max(0.25, min(float(data.get("speed", 1)), 4.0))
    stream = copy.deepcopy(hand_stream(hand).measures(start, end))
    stream.insert(0, m21.tempo.MetronomeMark(number=108 * speed))
    midi_path = Path(tempfile.mktemp(suffix=".mid"))
    wav_path = Path(tempfile.mktemp(suffix=".wav"))
    stream.write("midi", fp=str(midi_path))
    fluidsynth = shutil.which("fluidsynth")
    soundfont = next((p for p in [Path("/usr/share/sounds/sf2/FluidR3_GM.sf2"), Path("/usr/share/soundfonts/default.sf2")] if p.exists()), None)
    if not fluidsynth or not soundfont:
        return jsonify({"error": "FluidSynth or a GM soundfont is not installed. Install them to enable audio rendering."}), 503
    subprocess.run([fluidsynth, "-ni", "-F", str(wav_path), "-r", "44100", str(soundfont), str(midi_path)], check=True, capture_output=True)
    return send_file(wav_path, mimetype="audio/wav", as_attachment=False, download_name="piano-selection.wav")


@app.get("/")
def index():
    return send_from_directory(STATIC, "index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
