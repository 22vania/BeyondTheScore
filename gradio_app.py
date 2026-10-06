from pathlib import Path
import copy
import shutil
import subprocess
import tempfile
import wave

import gradio as gr
import music21 as m21
import numpy as np

ROOT = Path(__file__).resolve().parent
score = m21.converter.parse(str(ROOT / "allegretto_audiveris.mxl"))
TOTAL = max(len(p.getElementsByClass(m21.stream.Measure)) for p in score.parts)


def hand_stream(hand):
    if hand == "Both hands":
        return score
    suffix = "-Staff1" if hand == "Right hand" else "-Staff2"
    return next((p for p in score.parts if str(p.id).endswith(suffix)), score.parts[0])


def select_stream(hand, start, end):
    if start is None or end is None or int(start) != start or int(end) != end:
        raise ValueError(f"Invalid input: enter whole-number measures from 1 to {TOTAL}.")
    start, end = int(start), int(end)
    if start < 1 or end > TOTAL or end < start:
        raise ValueError(f"Invalid input: start and end must be between 1 and {TOTAL}, with start no greater than end.")
    return copy.deepcopy(hand_stream(hand).measures(start, end))


def read_wav(path):
    with wave.open(str(path), "rb") as source:
        channels = source.getnchannels()
        samples = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2").astype(np.float32)
    return samples.reshape(-1, channels).mean(axis=1) / 32768


def mix_hands(stems, right_volume, left_volume):
    if not stems:
        return None, "Choose a selection and press Play before adjusting the hand volumes."
    tracks = {side: read_wav(path) for side, path in stems.items()}
    length = max(map(len, tracks.values()))
    mixed = np.zeros(length, dtype=np.float32)
    for side, samples in tracks.items():
        level = (right_volume if side == "right" else left_volume) / 100
        mixed[:len(samples)] += samples * level
    output = Path(tempfile.mktemp(prefix="vanilla_mix_", suffix=".wav"))
    with wave.open(str(output), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(44100)
        target.writeframes((np.clip(mixed, -1, 1) * 32767).astype("<i2").tobytes())
    return str(output), "Hand volumes updated."


def render_audio(hand, start, end, speed, right_volume, left_volume):
    try:
        # Keep independent tracks so the sliders can remix the current result.
        if hand == "Both hands":
            parts = [("right", score.parts[0]), ("left", score.parts[-1])]
        else:
            parts = [("right" if hand == "Right hand" else "left", hand_stream(hand))]
        select_stream(hand, start, end)  # Validate before creating any files.
        bundled_synth = ROOT / "tools" / "fluidsynth-v2.6.1-win10-x86-cpp11" / "bin" / "fluidsynth.exe"
        synth = shutil.which("fluidsynth") or (str(bundled_synth) if bundled_synth.exists() else None)
        soundfont = next((p for p in [ROOT / "tools" / "GeneralUser-GS.sf2", ROOT / "tools" / "FluidR3_GM.sf2", Path("C:/soundfonts/FluidR3_GM.sf2")] if p.exists() and p.stat().st_size > 1_000_000), None)
        if not synth or not soundfont:
            raise RuntimeError("FluidSynth or the General MIDI soundfont is not installed.")
        stems = {}
        for side, part in parts:
            stream = copy.deepcopy(part.measures(int(start), int(end)))
            for measure in stream.recurse().getElementsByClass(m21.stream.Measure):
                if isinstance(measure.leftBarline, m21.bar.Repeat):
                    measure.leftBarline = None
                if isinstance(measure.rightBarline, m21.bar.Repeat):
                    measure.rightBarline = None
            stream.insert(0, m21.tempo.MetronomeMark(number=108 * float(speed)))
            midi = Path(tempfile.mktemp(suffix=".mid"))
            wav = Path(tempfile.mktemp(suffix=".wav"))
            stream.write("midi", fp=str(midi))
            subprocess.run([synth, "-ni", "-F", str(wav), "-r", "44100", str(soundfont), str(midi)], check=True, capture_output=True)
            stems[side] = str(wav)
        output, _ = mix_hands(stems, right_volume, left_volume)
        return output, f"Playing {hand.lower()}, measures {start}–{end}, at {speed}× speed.", stems
    except Exception as exc:
        return None, f"Error: {exc}", None


def play_selection(hand, start, end, speed, right_volume, left_volume):
    # One click captures one set of inputs. Keeping the status and render in
    # the same event prevents the second stage from reading an older value.
    yield None, "Processing…", None
    yield render_audio(hand, start, end, speed, right_volume, left_volume)


SLIDER_CSS = """
#speed-slider input[type="range"], #right-volume input[type="range"], #left-volume input[type="range"] { --slider-color: #fff; }
#speed-slider input[type="range"]::-webkit-slider-runnable-track,
#right-volume input[type="range"]::-webkit-slider-runnable-track,
#left-volume input[type="range"]::-webkit-slider-runnable-track {
    background: linear-gradient(to right, #fff var(--range_progress), #777 var(--range_progress)) !important;
}
#speed-slider input[type="range"]::-moz-range-progress,
#right-volume input[type="range"]::-moz-range-progress,
#left-volume input[type="range"]::-moz-range-progress { background: #fff !important; }
#speed-slider input[type="range"]::-webkit-slider-thumb,
#right-volume input[type="range"]::-webkit-slider-thumb,
#left-volume input[type="range"]::-webkit-slider-thumb {
    background: #fff !important; border: 2px solid #222 !important;
    box-shadow: 0 0 0 2px #fff !important;
}
#speed-slider input[type="range"]::-moz-range-thumb,
#right-volume input[type="range"]::-moz-range-thumb,
#left-volume input[type="range"]::-moz-range-thumb {
    background: #fff !important; border: 2px solid #222 !important;
    box-shadow: 0 0 0 2px #fff !important;
}
#playback-box { border: 1px solid #ddd; border-radius: 12px; padding: 16px; }
"""

with gr.Blocks(title="Vanilla Music") as demo:
    gr.Markdown("# Vanilla Music\n### Piano practice lab · Allegretto · 24 measures")
    with gr.Column():
        gr.Markdown("### 1. Which hand?")
        hand = gr.Radio(["Right hand", "Left hand", "Both hands"], value="Right hand", label="Hand")
        gr.Markdown("### 2. Which measures?")
        start = gr.Number(1, precision=0, label="Start measure")
        end = gr.Number(2, precision=0, label="End measure")
        gr.Markdown("### 3. Speed")
        speed = gr.Slider(0.5, 2, value=1, step=0.25, label="Playback speed (×)", elem_id="speed-slider")
    gr.Markdown("### 4. Playback")
    with gr.Row():
        play = gr.Button("▶ Play selection", variant="primary")
        repeat = gr.Button("↻ Repeat")
    with gr.Group(elem_id="playback-box"):
        audio = gr.Audio(label="Audio", type="filepath", autoplay=True)
        gr.Markdown("Adjust each hand’s volume for the current audio:")
        right_volume = gr.Slider(0, 200, value=100, step=5, label="Right hand volume (%)", elem_id="right-volume")
        left_volume = gr.Slider(0, 200, value=100, step=5, label="Left hand volume (%)", elem_id="left-volume")
    status = gr.Markdown("Choose all options above, then press Play selection.")
    stems = gr.State()
    playback_inputs = [hand, start, end, speed, right_volume, left_volume]
    play.click(play_selection, playback_inputs, [audio, status, stems])
    repeat.click(play_selection, playback_inputs, [audio, status, stems])
    for slider in (right_volume, left_volume):
        slider.change(mix_hands, [stems, right_volume, left_volume], [audio, status], trigger_mode="always_last")


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, css=SLIDER_CSS)
