# VaultVision 0.1 prototype
Screen-only Dark and Darker killfeed detection with OBS Replay Buffer saves. No game memory reads, injection, game hooks, or game-file changes. All OCR is local.

## Windows setup
1. Install Tesseract OCR for Windows (English language data). Set its executable path in the app. It is an external dependency, not bundled in this prototype.
2. In OBS create a dedicated source named `Dark and Darker`: Window Capture, using the Windows capture method, targeting the game. Do not use Game Capture for this design. Keep the source active in the current scene, showing the full 1920x1080 HUD.
3. Set video to 1080p/60 and recording encoder to NVIDIA NVENC H.264. Choose game audio and turn microphone off if desired. Configure the recording output folder.
4. Enable Replay Buffer, set 60 seconds, allow sufficient memory (e.g. 512 MB to begin), and start it. Actual duration can be limited by memory/bitrate; verify a manual replay.
5. Tools → WebSocket Server Settings: enable server on port 4455 and enable authentication. Enter the password in VaultVision; click Save password to retain it locally. The password is stored as plain text in `%LOCALAPPDATA%\\VaultVision\\obs-websocket-password.txt`, outside the app folder and repository. Open password file lets you edit it in your text editor; use only the password on one line, save, then restart VaultVision to autofill. You can also clear the field and click Save password to remove the stored value. Keep server access local.
6. Download the Windows artifact from GitHub Actions, extract the entire folder, and run VaultVision.exe. Alternatively install requirements and run `python app.py`.
7. Arm while controlling your character. Automatic name detection needs three consistent reads of the bottom-center name. A manual name override is available.
8. Disarm before menus, spectating, or switching characters; re-arm for the next match. This prototype does not yet reliably recognize game/menu/spectator states.

Detected events request a replay save immediately by default (0 seconds). The optional save delay is measured from recognition, not the actual kill; adding a delay reduces pre-event footage. Use 0 while measuring recognition latency. Logs include wall-clock timestamps, capture time, OCR time and detected feed-line count. OBS controls the clip length and destination. This version saves the complete buffer, not an exact 30-before/10-after trimmed clip. It reports a save *request*, not verified file completion. Closely spaced events before a save share its first deadline; later events can produce overlapping clips. No automatic deletion.

## Validation
`python -m unittest discover -v`

Offline video tests require ffmpeg on PATH and Tesseract:
`python offline.py path/to/video.mp4 --start 190 --duration 10`

The supplied 1080p sample produced one kill event (NerfRogueStill → Poragau, Castillon Dagger), with automatic identity. Uploaded gameplay is intentionally not committed.

## Known limitations / next work
This is a functional prototype, not a validated live-game release. OCR can miss/garble text; sampling runs as fast as local OCR permits, with a 0.5 second wait. Exact normalized names are required; no fuzzy attribution that could confuse other players. Same killer/victim pairs are deduplicated until absent for 180 seconds, so an unusually quick repeat can be suppressed. Automatic death support uses the feed; non-feed death transitions are not implemented. Identity is frozen after detected death and monitoring stops after its save. Test on a death recording before trusting it. Live OBS capture/audio, fullscreen behavior, performance and Windows executable have not been tested on the development Linux environment.

Next: add death fixtures, full-recording false-positive tests, OCR confidence and measured performance, lobby/spectator guards, save-completion confirmation, exact clip trimming, settings persistence, tray controls, and calibration for other HUD scales. Do not upload credentials or personal recordings to this public repository.

## Automatic OBS startup and clip previews
Opening VaultVision launches `C:\Program Files\obs-studio\bin\64bit\obs64.exe --startreplaybuffer --minimize-to-tray`, with the OBS binary folder as its working directory. Existing OBS instances are reused. With the saved WebSocket password, VaultVision connects and starts the replay buffer if needed. Replay Buffer must be enabled/configured in the OBS profile. OBS remains running when VaultVision closes.

The Saved Clips panel discovers OBS's last completed replay save while VaultVision is open, persists paths in `%LOCALAPPDATA%\VaultVision\clips.json`, and labels detected events. Files stay in the OBS output folder. Select a clip for a paused first-frame preview; Play/Pause and Restart play video with audio inside the app. Import clips adds earlier recordings. Deleted/moved recordings cannot play. Playback uses bundled FFpyPlayer/FFmpeg; no separate VLC installation is required. Monitoring continues while playback runs; decoding can add CPU load. Rapid saves between two-second polls may only expose the latest file; complete save-event subscription is future work. Event labels for externally triggered OBS saves may be generic. Windows startup and bundled playback require real-machine validation.
