"""Every interface string in one place.

The user interface is English. Romanian remains the default transcription LANGUAGE,
selected in Settings — it is not the language of the application chrome.

A future translation only needs a second copy of this module and one import switch;
no framework is involved on purpose.
"""
from __future__ import annotations

# ── Application ───────────────────────────────────────────────────────────────
APP_NAME = "TranscriptionLab"
# The wordmark breathes as two words; the window title and the taskbar keep the one-word name.
BRAND_WORDMARK = "Transcription Lab"
APP_TAGLINE = "Transcribe and review long group interviews"

# ── Orientation: where the researcher is in the four-step flow ────────────────
STEP_EYEBROW = "STEP {current} OF {total}"
NEXT_RECORDING = "Next: enter your provider key and start transcribing."
NEXT_TRANSCRIPTION = "Next: give the detected voices real names."
NEXT_SPEAKERS = "Next: choose a format and save the transcript."
NEXT_EXPORT = "Saved files open in Windows; the project keeps your corrections for later."

# ── Field guidance ────────────────────────────────────────────────────────────
KEY_HELPER = "Kept in memory for this session only, never written to disk."
# Shown on the first screen while no key has been entered, so a new user on a fresh
# install is told what they need before they pick a file rather than after.
BYOK_TITLE = "You will need your own API key"
BYOK_BODY = ("This app does not come with a transcription account. Choose your provider in "
             "Settings, then paste that provider's API key on the Transcription step. The "
             "key is held in memory for the session only and is never written to disk.")
BYOK_ACTION = "Open Settings"
RANGE_START_HELPER = "Empty starts from the beginning."
RANGE_END_HELPER = "Empty runs to the end of the recording."
RANGE_COST_NOTE = "Only the selected portion is sent to the provider, so it is what you are billed for."

# ── Navigation and shell ──────────────────────────────────────────────────────
NAV_RECORDING = "Recording"
NAV_TRANSCRIPTION = "Transcription"
NAV_SPEAKERS = "Speakers"
NAV_EXPORT = "Export"
NAV_LOCKED = "Finish the previous step to open {step}"
OPEN_PROJECT = "Open project"
SAVE_PROJECT = "Save project"
NEW_PROJECT = "New project"
SETTINGS = "Settings"
TOGGLE_THEME = "Switch theme"
HELP = "Help"
UNTITLED_PROJECT = "Untitled project"
SAVED = "Saved"
UNSAVED = "Unsaved changes"
API_CONFIGURED = "API key set"
API_MISSING = "No API key"

# ── Collapse controls ─────────────────────────────────────────────────────────
COLLAPSE_SECTION = "Minimise this section"
EXPAND_SECTION = "Expand this section"
COLLAPSE_SIDEBAR = "Minimise the sidebar"
EXPAND_SIDEBAR = "Expand the sidebar"

# ── Window controls ───────────────────────────────────────────────────────────
WINDOW_MINIMIZE = "Minimise"
WINDOW_MAXIMIZE = "Maximise"
WINDOW_RESTORE = "Restore down"
WINDOW_CLOSE = "Close"

# ── Welcome ───────────────────────────────────────────────────────────────────
WELCOME_TITLE = "Transcription for group interviews"
WELCOME_BODY = "Process long recordings, identify who spoke, and export documents ready for analysis."
WELCOME_FACT_LOCAL = "The original recording stays on this computer and is never modified."
WELCOME_FACT_UPLOAD = "Only what the chosen provider needs is sent; Settings states exactly what leaves the machine."
WELCOME_FACT_KEY = "API keys live in memory only and are never saved."
WELCOME_START = "Get started"
WELCOME_HOW = "How it works"

HELP_TITLE = "How it works"
HELP_NEW_HEADING = "Transcribe a new recording"
HELP_STEPS = ("1. Choose a recording stored on this computer.",
              "2. Enter the provider API key and start transcribing.",
              "3. Review who spoke and correct the text.",
              "4. Export Word, plain text, or JSON.")
HELP_OPEN_HEADING = "Continue an earlier interview"
HELP_OPEN_STEPS = ("1. Click Open project in the sidebar, or the button on this screen.",
                   "2. Choose the .transcript.json file saved from a previous session.",
                   "3. The transcript, speaker names and corrections load exactly as you left them.",
                   "4. Nothing is re-transcribed, so no API credit is spent.")
HELP_SHORTCUTS_HEADING = "While reviewing"
HELP_SHORTCUTS = ("Space plays or pauses — except while you are typing in a text field.",
                  "Ctrl+Enter marks the open turn reviewed and moves to the next unchecked one.",
                  "Click any turn to jump the audio to that exact second.",
                  "Click a word to jump to that word, when the provider timed them.")
HELP_UNDERSTOOD = "Got it"

# ── Opening an existing project ───────────────────────────────────────────────
OPEN_EXISTING_TITLE = "Already have a transcript?"
OPEN_EXISTING_BODY = ("Open a .transcript.json saved earlier to keep reviewing it. "
                      "Nothing is sent to a provider and no credit is spent.")
OPEN_EXISTING_ACTION = "Open a saved project"

# ── Recording screen ──────────────────────────────────────────────────────────
RECORDING_TITLE = "Recording"
RECORDING_SUBTITLE = "Pick the recording and decide how much of it to transcribe."
EMPTY_RECORDING_TITLE = "Select a recording"
EMPTY_RECORDING_BODY = "M4A, WAV, MP3, MP4, AAC, FLAC, or WEBM"
EMPTY_RECORDING_HINT = "The file stays on this computer. Nothing is sent anywhere until you start transcribing."
CHOOSE_FILE = "Choose file"
CHANGE_FILE = "Change file"
CONTINUE = "Continue"
FIELD_DURATION = "Duration"
FIELD_SIZE = "Size"
FIELD_FORMAT = "Format"
FIELD_CHANNELS = "Channels"
FIELD_SAMPLE_RATE = "Sample rate"
FIELD_SOURCE_QUALITY = "Source handling"
FIELD_ESTIMATED_CHUNKS = "Estimated fragments"
FIELD_STRATEGY = "Strategy"
QUALITY_ORIGINAL = "Keep compressed source"
QUALITY_COMPATIBLE = "AAC mono {bitrate} kbps"
STRATEGY_COPY = "Stream copy when safe, re-encode only if needed"
STRATEGY_ENCODE = "Re-encode every fragment"
QUALITY_TITLE = "Audio preparation"
RADIO_ORIGINAL = "Keep the compressed source when it is safe"
RADIO_COMPATIBLE = "Force AAC mono for compatibility"

# ── Time range ────────────────────────────────────────────────────────────────
RANGE_TITLE = "Portion to transcribe"
RANGE_SUBTITLE = "Leave both fields empty to transcribe the whole recording."
RANGE_START = "Start (hh:mm:ss)"
RANGE_END = "End (hh:mm:ss)"
RANGE_FULL = "Transcribing the full recording · {duration}"
RANGE_PARTIAL = "Transcribing {start} to {end} · {duration} of {total}"
RANGE_ERROR_FORMAT = "Use mm:ss or hh:mm:ss."
RANGE_ERROR_ORDER = "Start must come before end."
RANGE_ERROR_BOUNDS = "The range must fall inside the recording ({total})."
RANGE_ERROR_EMPTY = "The selected range is too short to transcribe."
RANGE_CLIP_CREATED = "Extracted {duration} starting at {start}."

# ── Upload preparation ────────────────────────────────────────────────────────
COMPRESS_STARTED = "Preparing a compact copy for upload ({size}); this takes a moment."
COMPRESS_DONE = "Compact copy ready: {before} reduced to {after}. Audio quality for speech is unaffected."

# ── Transcription screen ──────────────────────────────────────────────────────
TRANSCRIPTION_TITLE = "Transcription"
TRANSCRIPTION_SUBTITLE = "Enter the provider key and start. The app stays usable while it runs."
START_TRANSCRIPTION = "Start transcription"
CANCEL = "Cancel"
READY = "Ready to transcribe"
MODEL_LINE = "Model {model}"
STAGE_FRAGMENT = "Fragment {current} of {total}"
STAGE_WHOLE_FILE = "Whole recording, single request"
ELAPSED = "Elapsed {elapsed}"
PROGRESS_STAGES = ("Analysis", "Audio preparation", "Transcription", "Merging", "Finishing")
ACTIVITY_LOG = "Activity log"
ACTIVITY_LOG_SUBTITLE = "Compact detail for diagnostics"
ACTIVITY_LOG_EMPTY = "Technical activity will appear here."
DIAGNOSTICS = "DIAGNOSTICS"
COPY_DETAILS = "Copy details"

# ── Speakers screen ───────────────────────────────────────────────────────────
SPEAKERS_TITLE = "Speakers"
SPEAKERS_SUBTITLE = "Give each detected voice a real name, then correct any wording."
IDENTITIES = "Identities"
COLLAPSE_IDENTITIES = "Hide the speaker panel"
EXPAND_IDENTITIES = "Show the speaker panel"
IDENTITIES_COUNT = "{count} labels detected"
IDENTITIES_NONE = "No labels from this provider"
IDENTITY_STATS = "{count} turns · {duration}"
# One line per identity instead of three: the raw label, the count and the airtime together.
IDENTITY_META = "{speaker} · {count} turns · {duration}"
# The diarization state belongs beside the speakers it describes, not above the transcript.
DIARIZATION_GLOBAL = "Identified across the whole recording"
DIARIZATION_FRAGMENTED = "Labelled per fragment — confirm before exporting"
WORKBENCH_META = "{turns} turns · {speakers} speakers · {duration}"

# ── Review progress ───────────────────────────────────────────────────────────
PROGRESS_LABEL = "{checked} / {total} checked, {percent}%"
PROGRESS_NONE = "Nothing checked yet"
PROGRESS_COMPLETE = "All {total} turns checked"
ONLY_UNCHECKED = "Only unchecked"
ONLY_UNCHECKED_TOOLTIP = "Hide the turns already reviewed"
ALL_CHECKED = "Nothing left unchecked here."
RESUME = "Resume"
RESUME_TOOLTIP = "Go back to {stamp}, where you left off"
MARK_CHECKED = "Checked"
MARK_CHECKED_TOOLTIP = "Mark this turn reviewed"
MARK_NEXT_HINT = "Ctrl+Enter marks this turn and moves to the next unchecked one."
REVIEW_DONE = "Every turn is checked."
SHOW_ORIGINAL = "Show original"
HIDE_ORIGINAL = "Hide original"
SEEK_WORDS = "Click a word to jump there"
EDIT_TEXT = "Back to editing"
APPLY_NAME = "Apply name"
CONTINUE_TO_EXPORT = "Continue to export"
BANNER_GLOBAL = "Speakers were identified across the whole recording. You only need to assign real names."
BANNER_FRAGMENTED = "Labels were created separately for each fragment. Confirm identities before exporting."
BANNER_NO_DIARIZATION = "This provider returns no speaker labels; you will name and split speakers manually."
NOW_SPEAKING = "Now showing"
PLAY_TURN = "Play this turn"

# ── Audio player ──────────────────────────────────────────────────────────────
PLAYER_PLAY = "Play"
PLAYER_PAUSE = "Pause"
PLAYER_HINT = "Space plays or pauses. Click a turn or a word to jump to it."
PLAYER_NO_AUDIO = "No recording connected"
PLAYER_SPEED = "Speed"

# ── Review helpers ────────────────────────────────────────────────────────────
LOW_CONFIDENCE_COUNT = "{count} words the model was unsure of"
LOW_CONFIDENCE_TURNS = "{count} turns the model was unsure of"
LOW_CONFIDENCE_NEXT = "Next uncertain"
LOW_CONFIDENCE_NONE = "Nothing flagged as uncertain"
FIND_REPLACE = "Find and replace"
FIND_LABEL = "Find"
REPLACE_LABEL = "Replace with"
FIND_CASE = "Match case"
FIND_WHOLE_WORD = "Whole word"
FIND_COUNT = "{count} matches in {turns} turns"
FIND_COUNT_NONE = "No matches"
FIND_COUNT_EMPTY = "Type something to find"
FIND_REPLACE_ALL = "Replace all"
FIND_UNDO = "Undo replace"
FIND_CLOSE = "Close find"
FIND_DONE = "Replaced {count} occurrences in {turns} turns."
FIND_UNDONE = "Replacement undone."
FIND_HINT = "Text only — timings and speaker labels never change. Esc closes."
INSERT_TIMESTAMP = "Insert timestamp"
INSERT_TIMESTAMP_HINT = "Ctrl+T puts the current playback time into the text, for citation."

# ── Reassigning a turn, and merging two labels into one person ────────────────
REASSIGN_LABEL = "Speaker"
REASSIGN_TOOLTIP = "Move this turn to another speaker"
REASSIGN_DONE = "Turn moved to {speaker}."
MERGE_INTO = "Merge into another speaker"
MERGE_MENU_ITEM = "Merge into {speaker}"
MERGE_TITLE = "Merge two speakers"
MERGE_BODY = ("Every turn currently labelled {source} ({count} turns · {duration}) will be moved to "
              "{target}, and {source} will disappear from this list.\n\n"
              "Only the speaker labels change. Timings, wording and word timestamps stay exactly as they are.")
MERGE_CONFIRM = "Merge"
MERGE_DONE = "{count} turns moved to {target}."
MERGE_UNAVAILABLE = "There is only one speaker to merge."
SETTINGS_REVIEW = "Review and playback"
SETTINGS_AUTO_REWIND = "Rewind when pausing"
SETTINGS_AUTO_REWIND_SECONDS = "Rewind by (seconds)"
SETTINGS_AUTO_REWIND_HINT = "Stepping back a moment means resuming catches the start of the word."
AUDIO_MISSING_TITLE = "Audio not found. Locate the recording to enable playback."
AUDIO_MISSING_BODY = "The transcript, speakers and corrections are all loaded — only playback needs the file."
AUDIO_LOCATE = "Locate audio"
AUDIO_DISMISS = "Dismiss"
AUDIO_DIALOG_TITLE = "Locate the recording"
AUDIO_CONNECTED = "Audio reconnected: {filename}."
AUDIO_MISMATCH_TITLE = "That file does not match"
AUDIO_MISMATCH_BODY = ("The project was transcribed from {expected} ({size}). The file you chose is "
                       "{chosen} ({chosen_size}). Use it anyway?")
AUDIO_UNREADABLE = "That file could not be opened as audio."
WORDS_HEADING = "Click a word to jump to it"
PAGE_PREVIOUS = "Previous"
PAGE_NEXT = "Next"
PAGE_POSITION = "Page {current} of {total}"

CLOSE_INSPECTOR = "Close inspector"
INSPECTOR_TITLE = "Selected turn"
INSPECTOR_EMPTY_TITLE = "Inspector"
INSPECTOR_EMPTY_BODY = "Select a turn to see details and make corrections."
INSPECTOR_ORIGINAL = "ORIGINAL TEXT"
INSPECTOR_CORRECTED = "Corrected text"
INSPECTOR_CONFIDENCE = "Confidence {percent}%"
INSPECTOR_WORDS = "{count} timed words"
SAVE_CORRECTION = "Save correction"
REVERT_CORRECTION = "Revert to original"
PLAY_RANGE = "Play this range"

# ── Export screen ─────────────────────────────────────────────────────────────
EXPORT_TITLE = "Export"
EXPORT_SUMMARY = "{turns} turns · {speakers} participants · {duration}"
EXPORT_OPTIONS = "Document options"
EXPORT_DOC_TITLE = "Document title"
EXPORT_PROJECT_ID = "Interview identifier"
EXPORT_DATE = "Interview date"
EXPORT_NOTES = "Notes"
EXPORT_TIMESTAMPS = "Include timestamps"
EXPORT_NOTICE = "Include the automatic-transcription notice"
EXPORT_ORIGINAL_LABELS = "Include original labels in JSON"
EXPORT_WORD = "Word"
EXPORT_WORD_BODY = "Formatted for reading and archiving. The usual choice for sharing with colleagues."
EXPORT_TEXT = "Text"
EXPORT_TEXT_BODY = "Plain text, no formatting. Best for pasting into analysis software."
EXPORT_JSON = "JSON"
EXPORT_JSON_BODY = "Every timestamp, label and confidence score. For coding tools and reproducibility."
EXPORT_SAVE = "Save {format}"
EXPORT_NO_DESTINATION = "No destination chosen yet"

# ── Settings screen ───────────────────────────────────────────────────────────
SETTINGS_TITLE = "Settings"
SETTINGS_SUBTITLE = "Appearance, transcription provider, and local tools."
SETTINGS_INTERFACE = "Interface"
SETTINGS_APPEARANCE = "Appearance"
APPEARANCE_LIGHT = "Light"
APPEARANCE_DARK = "Dark"
APPEARANCE_SYSTEM = "System"
SHOW_WELCOME_AGAIN = "Show the introduction again"
SETTINGS_TRANSCRIPTION = "Transcription"
SETTINGS_PROVIDER = "Transcription provider"
SETTINGS_LANGUAGE = "Recording language"
LANGUAGE_RO = "Romanian"
LANGUAGE_EN = "English"
SETTINGS_EXPECTED_SPEAKERS = "Expected number of speakers"
SETTINGS_EXPECTED_HINT = "Leave empty for automatic detection"
SETTINGS_ENDPOINT_URL = "Endpoint base URL"
SETTINGS_ENDPOINT_URL_HINT = "https://example.org/v1"
SETTINGS_ENDPOINT_MODEL = "Model name"
SETTINGS_ENDPOINT_MODEL_HINT = "whisper-1"
SETTINGS_ENDPOINT_PRIVACY = "The address, model, and key stay in memory only; they are never saved or exported."
SETTINGS_SPEAKERS_BOUND = "The expected count is enforced by the diarizer."
SETTINGS_SPEAKERS_ADVISORY = "The expected count is a hint for this provider."
SETTINGS_SPEAKERS_UNUSED = "This provider does not diarize, so the speaker count has no effect."
SETTINGS_AUDIO = "Audio preparation"
SETTINGS_AUDIO_NOTE = "Applies to the provider that fragments the recording locally."
SETTINGS_CHUNK_LIMIT = "Fragment limit (MB)"
SETTINGS_BITRATE = "AAC fallback (kbps)"
SETTINGS_OVERLAP = "Overlap (seconds)"
SETTINGS_INCLUDE_PATH = "Include the source path in JSON"
SETTINGS_DIAGNOSTIC = "Diagnostic logging"
SETTINGS_SAVE = "Save settings"
SETTINGS_FFMPEG = "FFmpeg"
SETTINGS_FFMPEG_UNAVAILABLE = "Unavailable"
SETTINGS_FFMPEG_NO_PATH = "No path configured"
CHOOSE_FOLDER = "Choose folder"

# ── Dialogs and notifications ─────────────────────────────────────────────────
CLOSE = "Close"
DISCARD = "Discard"
PROCEED = "Continue"
BUSY_TITLE = "Processing in progress"
BUSY_BODY = "Cancel the run and wait for the current request to finish."
UNSAVED_TITLE = "Unsaved changes"
UNSAVED_BODY = "The current project has unsaved changes. Continue anyway?"
FFMPEG_MISSING_TITLE = "FFmpeg is not available"
FFMPEG_MISSING_BODY = "The tools needed for audio processing were not found."
FFMPEG_NOT_FOUND = "{tool}: not found"
FFMPEG_INSTRUCTIONS = "Instructions"
FFMPEG_INSTRUCTIONS_TITLE = "FFmpeg instructions"
FFMPEG_INSTRUCTIONS_BODY = ("Install it with WinGet, or choose a folder that contains both ffmpeg.exe and ffprobe.exe.\n\n"
                            "winget install --id Gyan.FFmpeg -e")
FFMPEG_INVALID_FOLDER_TITLE = "Invalid folder"
FFMPEG_INVALID_FOLDER_BODY = "The folder must contain working copies of ffmpeg.exe and ffprobe.exe."
COPY_COMMAND = "Copy command"

# ── File dialogs ──────────────────────────────────────────────────────────────
DIALOG_CHOOSE_RECORDING = "Choose a recording"
DIALOG_CHOOSE_FFMPEG = "Choose the FFmpeg folder"
DIALOG_SAVE_EXPORT = "Save export"
DIALOG_SAVE_PROJECT = "Save project"
DIALOG_OPEN_PROJECT = "Open project"
DEFAULT_PROJECT_FILENAME = "project.transcript.json"
EXPORT_FILENAME = "{stem}_transcript.{ext}"

# ── Wording inside the exported Word document ────────────────────────────────
# It reaches the reader of the transcript rather than the researcher at the screen, so it
# lives here with everything else a human reads. The transcript body stays in whatever
# language the interview was conducted in; only these labels are the application speaking.
DOC_DEFAULT_TITLE = "Group interview transcript"
DOC_SOURCE_FILE = "Source file"
DOC_GENERATED = "Generated"
DOC_DURATION = "Recording length"
DOC_MODEL = "Model used"
DOC_PROJECT_ID = "Project identifier"
DOC_INTERVIEW_DATE = "Interview date"
DOC_NOTES = "Notes"
DOC_NOTICE = ("Note: transcription and speaker identification are automatic and require "
              "manual verification.")

# ── Controller messages that reach the activity log ───────────────────────────
LOG_FILE_ANALYSED = "File analysed."
LOG_MERGED_CHRONOLOGICALLY = "Transcript merged chronologically."
LOG_GLOBAL_SPEAKERS = "Speakers were identified across the whole recording."
LOG_FINISHED = "Transcription finished."
ERROR_ALREADY_RUNNING = "A transcription is already running."
ERROR_NO_RECORDING = "Select a valid recording first."
ERROR_SOURCE_MISSING = "The original audio file is no longer available."
ERROR_FFMPEG_MISSING = "FFmpeg is not available."
ERROR_METADATA_MISSING = "Recording metadata is missing."
ERROR_PREVIEW_FAILED = "The audio preview could not be created: {detail}"
ERROR_INCOMPATIBLE_PROJECT = "This file is not a compatible transcription project."
