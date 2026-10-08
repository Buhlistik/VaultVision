# VaultVision
Automatic Dark and Darker kill highlights using local screen OCR and the OBS Replay Buffer. VaultVision does not read game memory, modify game files, or inject into the game.

## Windows setup
1. Install Tesseract OCR with English language data. VaultVision remembers your executable location; if it cannot find it, use Settings → Choose OCR executable once.
2. Configure an OBS source named `Dark and Darker` showing your full 1920×1080 gameplay HUD. Select that source in VaultVision Settings.
3. Configure the recording encoder/audio/output folder in OBS. Enable the Replay Buffer and set a sufficient duration, usually 60 seconds.
4. Enable the OBS WebSocket server on port 4455 with authentication. Enter and save its password in VaultVision Settings.
5. Download the [latest Windows release](https://github.com/Buhlistik/VaultVision/releases/tag/latest), extract the entire ZIP, and open VaultVision.exe.

VaultVision launches OBS minimized with its replay buffer, waits for readiness, and begins monitoring automatically. Closing VaultVision also closes OBS normally, including its active-output confirmation.

## Automatic states and controls
- The health bar confirms gameplay. The character name is read automatically and frozen during that match.
- Spectator controls or the death menu disable kill capture. Confirmed lobby detection clears that lock and the previous character state.
- The HUD-loss timeout and character override have been removed. Missing HUD during a floor transition preserves match state; return-to-lobby detection resets it.
- The status area explains the current task and shows how recently a screen check completed.
- **Pause automatic clips / Resume automatic clips** is an explicit override. A manual pause persists until you resume, even after OBS reconnects.
- **Save clip now** saves an OBS replay independently of automatic monitoring, including while paused.
- **Include deaths** is optional and off by default.
- **Save delay** is measured from event recognition, not the actual kill. OBS controls replay duration; VaultVision saves the entire buffer rather than trimming it.

If pausing with a pending highlight, VaultVision requests that replay before stopping. Resuming re-reads your identity and retains recent-event deduplication until a confirmed lobby reset.

## Killfeed row tracking
The ten feed rows are OCRed separately. Before the feed fills, new entries append below existing rows. Once full, multiple existing entries confirm upward movement, including several new kills between scans. Earlier clean reads are preserved when the corresponding shifted row becomes unreadable. New kill attribution still requires your exact normalized character name; tolerant matching only associates previously observed entries. Pixel-identical rows reuse OCR results. A lobby reset clears row state. This does not guarantee recovery of text that was never readable.

## Clip library
Completed OBS saves appear in the clip library. Import can add existing recordings.
- Play/pause, restart, volume and timeline scrubbing work in the embedded player.
- **Rename** saves a display title without renaming or rewriting the video file.
- **Fullscreen** uses the existing decoder. Escape exits, Space toggles playback, and Left/Right seek five seconds.
- Playback remains paused when selecting a different clip. Video playback can add load while it is active.
- Missing or moved video files are not loaded. Rapid replay saves between OBS polls may expose only the latest path.

## Settings and diagnostics
Settings and clip titles survive app updates. Local files are under `%LOCALAPPDATA%\\VaultVision`:
- `settings.json`: capture and playback preferences.
- `clips.json`: video paths, event labels and display titles.
- `obs-websocket-password.txt`: saved password, stored as plain text.
- `activity.log`: timestamped detection and timing diagnostics, rotated at 5 MB with three backups.
- `crash.log`: fatal errors and GUI callback failures.

The activity log is hidden from the main UI. Open it through **Settings → Open activity log** when reporting a problem.

## Updating
Close VaultVision, then run `Update-VaultVision.cmd` beside the executable. It downloads the latest successful release, verifies its checksum and replaces application files while preserving settings and recordings. Keep the companion PowerShell script alongside it.

## Validation and limitations
Run `python -m unittest discover -v`. Windows CI also checks construction of the interface and entering/exiting fullscreen with a shared decoder. Linux checks cannot verify the native Windows appearance, OBS behavior or audio.

OCR can miss or garble text. Attribution uses your complete normalized name, including when compass OCR precedes the killer token; it does not fuzzy-match other players. Recent killer/victim pairs are deduplicated for 180 seconds, so an unusually quick repeated kill of the same player can be suppressed. Detection speed depends on capture and OCR performance. Other HUD resolutions/scales need validation. Uploaded gameplay and credentials are never committed.
