# FL Studio Producer Brain — Instructions for Claude

This MCP server gives you full knowledge of the user's FL Studio setup on Windows.
Read this before using any tools so you can make smart decisions instead of guessing.

## Recommended startup flow

When a new conversation starts, do this in order:

1. Call `read_plugins(force_rescan=False)` — loads the cached plugin list (instant).
2. If the user mentions they have new samples, call `scan_samples` on their folder. Otherwise ask if they've run a scan before.
3. Once you know what plugins they have, call `research_plugin` for the 2-3 most common ones (Serum, Kontakt, Vital, etc.) so you have context for recommendations.

Only do steps 1-3 if the user's request actually needs that context. For simple questions, answer directly.

## Tool-by-tool guidance

### scan_samples
- This can take several minutes on large libraries (2000+ files). Warn the user.
- Check `force_rescan=False` first — it uses cache and returns instantly if already scanned.
- After scanning, report the breakdown by type so the user knows what was found.
- Confidence below 0.5 means the classifier is guessing. Treat those results as uncertain.

### get_samples
- Always filter by `type` when the user asks for a specific drum sound.
- Use `min_confidence=0.65` for casual browsing, `0.8+` when you need reliable results.
- The `brightness` field (spectral centroid in Hz) is useful for picking the right character:
  - Kick: typically 200–1500 Hz
  - Snare: 1500–5000 Hz
  - Hi-hat (closed): 5000–12000 Hz
  - 808: below 300 Hz

### read_plugins
- The `type` field is `generator` (instruments), `effect`, or `unknown` (raw VST scan).
- `nfo_path` being set means FL Studio has it properly registered in its database.
- If a plugin appears with `type=unknown`, it was found in a system VST folder but not in FL's database — it may not be usable in FL.

### research_plugin
- Built-in data exists for: Serum, Massive, Massive X, Sylenth1, Kontakt, Vital, Omnisphere, Nexus, 3xOsc, Harmor.
- For unlisted plugins, it does a Wikipedia/web lookup which may return incomplete data.
- Always cache research — never call this twice for the same plugin in one session.

### find_presets → install_preset → load_preset_in_fl (the preset pipeline)
Run them in sequence:

```
1. find_presets(plugin_name="Serum", genre="trap", sound_type="bass")
   → returns list with URLs

2. install_preset(preset_url="...", plugin_name="Serum", preset_name="Trap Bass Pack")
   → downloads + installs, returns local_path

3. load_preset_in_fl(preset_path="C:\\..\\preset.fst")
   → opens FL browser (F8), user drags to channel rack
```

- Always confirm with the user before calling `install_preset` — it writes files to disk.
- `load_preset_in_fl` requires FL Studio to be open. If it fails, give the user the fallback path printed in the response.
- pyautogui automation is the most brittle part of this server. If it fails, always fall back to the manual instruction in the response — never retry in a loop.

### send_notes
- Requires LoopMIDI installed on Windows + a virtual port created.
- In FL Studio: Options → MIDI Settings → enable the LoopMIDI input port + assign it.
- Notes use beats as the time unit, not milliseconds. BPM is needed for correct timing.
- Common patterns you can generate:

  **UK Drill hi-hat pattern (130 BPM, 1 bar):**
  ```json
  [
    {"note": 42, "velocity": 90, "duration": 0.125, "time": 0},
    {"note": 42, "velocity": 70, "duration": 0.125, "time": 0.25},
    {"note": 46, "velocity": 80, "duration": 0.25,  "time": 0.375},
    {"note": 42, "velocity": 90, "duration": 0.125, "time": 0.5},
    {"note": 42, "velocity": 65, "duration": 0.125, "time": 0.75},
    {"note": 46, "velocity": 85, "duration": 0.25,  "time": 0.875}
  ]
  ```

  Standard MIDI drum note numbers:
  - 36 = Kick, 38 = Snare, 42 = Hi-hat closed, 46 = Hi-hat open
  - 49 = Crash, 51 = Ride, 39 = Clap, 37 = Side stick

### read_project
- Requires `pyflp` installed. If it fails, the error message tells the user to install it.
- pyflp support varies by FL Studio version. FL Studio 21 is best supported.
- Use this to understand what's already in a project before making recommendations.

### suggest_for_genre
- This is the high-level entry point for "I want to make X music" requests.
- It combines get_samples + read_plugins + find_presets in one call.
- Use it when the user asks a broad question. Use individual tools for specific tasks.

## Genre quick-reference

| Genre | BPM range | Key sounds | Best plugins |
|-------|-----------|------------|--------------|
| UK Drill | 140-145 | Sliding 808, rolling hi-hats, dark minor chords | Serum, Kontakt |
| Trap | 130-160 | Triplet hi-hats, heavy 808, snare rolls | Serum, Kontakt, 3xOsc |
| House | 120-130 | 4-on-floor kick, off-beat open hi-hat, chord stabs | Sylenth1, Serum |
| Lo-Fi | 70-90 | Dusty drums, jazz chords, vinyl noise | Kontakt, Vital |
| EDM | 128-135 | Supersaws, pumping sidechain, big drops | Serum, Sylenth1, Nexus |
| DnB | 165-175 | Breakbeats, reese bass, amen chops | Serum, Massive |
| Ambient | 60-80 | Long pads, textural FX, slow attack | Omnisphere, Vital |

### generate_beat
This is the main music creation tool. Use it when the user says anything like "create a beat", "make music", "generate a trap beat", etc.

**Workflow:**
```
generate_beat(genre="trap", key="F#", bpm=140, bars=4, include=["all"])
→ Returns midi_file path (e.g. C:\Users\...\beats\trap_F#pentatonic_minor_140bpm.mid)
→ User imports in FL Studio: File → Import → MIDI file
→ Assign instruments per channel:
    - Channel 10 (drums): FPC or any drum sampler
    - Channel 2 (bass): 3xOsc / Serum for 808 bass
    - Channel 3 (melody): Serum / Vital / any synth
    - Channel 4 (chords): Pad synth or Serum
```

**Key decisions:**
- Pick a key that fits the mood: F# minor (dark trap), C minor (drill), A minor (versatile)
- If bpm omitted, the tool picks a genre-appropriate BPM automatically
- `bars=4` is a standard loop; use `bars=8` for a longer phrase
- You can generate only specific tracks: `include=["drums", "bass"]`
- Supported genres: trap, uk drill, drill, house, lo-fi, hip hop, boom bap, edm, reggaeton, afrobeat, dancehall
- Supported scales: minor, major, pentatonic_minor, pentatonic_major, dorian, phrygian, blues

**After generating**, tell the user:
1. The exact path of the .mid file
2. Which key and chord progression was used
3. How to assign instruments in FL Studio per channel
4. That they can call generate_beat again with different params to iterate

## What this server cannot do

- It cannot hear audio or listen to a project playing back.
- It cannot change knobs/parameters inside a plugin's own GUI (only load presets).
- It cannot create or modify MIDI inside FL Studio's piano roll directly — it sends notes via MIDI, which FL must be set to receive.
- It cannot read or write to FL Studio's mixer automation clips.
- pyautogui actions depend on screen resolution and FL Studio window position. If the user is in fullscreen mode, some UI actions may fail.

## Error handling

If a tool returns an `error` key, always:
1. Read the full error message — it includes actionable instructions.
2. Check if it's a missing dependency (pip install ...) and tell the user.
3. Never retry a failed tool call with the same exact arguments without changing something.
4. For `load_preset_in_fl` failures, always give the manual fallback path from the response.
