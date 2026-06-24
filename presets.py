"""Focus Music style presets for Suno API.
Each preset = (name, style_prompt, negative_tags, bpm, duration_seconds)
Tweak the style_prompt lines to match the vibe you want; Suno reads them as guidance.
"""

PRESETS = {
    "deep_focus": {
        "label": "Deep Focus (lo-fi + piano, long form)",
        # Length tricks: mention "8 minutes", "extended mix", "continuous evolving",
        # "no fade out", "seamless loop" to push Suno away from short 1-2 min clips.
        # Variation comes from Suno's own engine — same prompt = 4 distinct takes.
        "style": (
            "lo-fi hip hop, mellow piano chords, soft vinyl crackle, slow kick and hat, "
            "warm bass, deep sustained sub-bass, atmospheric pads, gentle tape hiss, "
            "instrumental, no vocals, no lyrics, study music, deep focus, work music, "
            "concentration music, 70 BPM, 8 minutes, extended mix, continuous evolving "
            "structure, seamless loop, no fade out, no abrupt ending, long-form, "
            "hypnotic repetition, gentle progression, immersive ambient"
        ),
        "negative": "vocals, lyrics, singing, heavy drums, distortion, aggressive, loud, fast tempo, sudden changes, fade out, short, abrupt ending",
        "bpm": 70,
        "duration": 480,  # 8 min target — Suno will cap at model max (typically 2-4 min on free)
    },
    "calm_piano": {
        "label": "Calm Piano (ambient focus, long form)",
        "style": (
            "ambient piano, soft evolving pads, no drums, no percussion, no beats, "
            "dreamy reverb, soft attack, gentle decay, focus music, deep focus, work music, "
            "concentration music, instrumental, no vocals, no lyrics, 60 BPM, 8 minutes, "
            "extended mix, continuous evolving structure, seamless loop, no fade out, "
            "no abrupt ending, long-form, hypnotic repetition, gentle progression, "
            "immersive ambient, meditation, peaceful"
        ),
        "negative": "vocals, lyrics, singing, drums, beats, percussion, guitar, bass, sudden changes, fade out, short, abrupt ending, aggressive",
        "bpm": 60,
        "duration": 480,
    },
    "coffee_shop": {
        "label": "Coffee Shop (soft jazz)",
        "style": "soft jazz, acoustic guitar, brushed drums, upright bass, café ambience, background music, instrumental, 90 BPM",
        "negative": "vocals, lyrics, electric guitar, heavy bass, EDM, loud",
        "bpm": 90,
        "duration": 180,
    },
    "chill_beats": {
        "label": "Chill Beats (work energy)",
        "style": "chillhop, jazzy piano sample, boom bap drums, mellow bass, vinyl texture, instrumental work music, 85 BPM",
        "negative": "vocals, lyrics, fast tempo, EDM, harsh synths",
        "bpm": 85,
        "duration": 180,
    },
    "nature_ambient": {
        "label": "Nature Ambient (rain + pad)",
        "style": "ambient, soft synth pad, gentle rain sounds, distant thunder, no drums, deep focus, 55 BPM",
        "negative": "vocals, lyrics, beats, percussion, harsh sounds",
        "bpm": 55,
        "duration": 240,
    },
    "minimal_techno": {
        "label": "Minimal Techno (deep work)",
        "style": "minimal techno, deep kick, soft hi-hat, sub bass, hypnotic loop, no vocals, deep focus, 120 BPM",
        "negative": "vocals, lyrics, melodic, pop, bright synths",
        "bpm": 120,
        "duration": 240,
    },
}


def list_presets():
    for key, p in PRESETS.items():
        print(f"  {key:20s}  {p['label']}  ({p['bpm']} BPM, {p['duration']}s)")


def get_preset(name: str) -> dict:
    if name not in PRESETS:
        raise SystemExit(
            f"Unknown preset '{name}'. Run with --list to see options."
        )
    return PRESETS[name]
