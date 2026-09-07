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
NAV_HOME_TOOLTIP = "Home — what this application does, and how to use it"
APP_TAGLINE = "Transcribe and review interview recordings"

# ── Orientation: where the researcher is in the four-step flow ────────────────
STEP_EYEBROW = "STEP {current} OF {total}"
NEXT_RECORDING = "Next: enter your provider key and start transcribing."
NEXT_TRANSCRIPTION = "Next: give the detected voices real names."
NEXT_EXPORT = "Saved files open in Windows; the project keeps your corrections for later."

# ── Field guidance ────────────────────────────────────────────────────────────
API_MISSING_START = "Add your provider's API key in Settings before starting."
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
NAV_SPEAKERS = "Review"
NAV_EXPORT = "Export"
NAV_LOCKED = "Finish the previous step to open {step}"
OPEN_PROJECT = "Open project"
SAVE_PROJECT = "Save project"
SAVE_PROJECT_TOOLTIP = "Choose where to save the project (Ctrl+S)"
SAVE_PROJECT_TO = "Save to {name} (Ctrl+S) · Ctrl+Shift+S saves elsewhere"
SAVED_TO = "Saved to {name}."
SAVE_PROJECT_EMPTY = "There is no transcript to save yet"
NEW_PROJECT = "New project"
SETTINGS = "Settings"
TOGGLE_THEME = "Switch theme"
HELP = "Help"
UNTITLED_PROJECT = "Untitled project"
SAVED = "Saved"
UNSAVED = "Unsaved changes"
API_CONFIGURED = "API key set"
API_MISSING = "Add an API key"
API_CONFIGURED_TOOLTIP = "The key for this provider is set. Open Settings to change it."
API_MISSING_TOOLTIP = "Open Settings to enter your provider's key"

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
WELCOME_TITLE = "Turn an interview recording into a transcript you can work with"
WELCOME_BODY = ("One person or twelve, twenty minutes or three hours. The recording is "
                "transcribed, split by speaker, and handed to you to correct, mark up and "
                "export.")
WELCOME_FACT_LOCAL = "The original recording stays on this computer and is never modified."
WELCOME_FACT_UPLOAD = "Only what the chosen provider needs is sent; Settings states exactly what leaves the machine."
WELCOME_FACT_KEY = "API keys live in memory only and are never saved."
WELCOME_START = "Get started"
WELCOME_HOW = "How it works"

HELP_TITLE = "How it works"
HELP_NEW_HEADING = "Transcribe a recording"
HELP_STEPS = (
    "1. Settings: paste your API key and pick the language of the recording. The key is "
    "held in memory for this session and never written to disk.",
    "2. Recording: choose the audio file. Your file is never modified — a copy is what "
    "gets prepared and sent. Set a range here if you only want part of it.",
    "3. Transcription: press Start and wait. What you chose goes to the provider you "
    "picked and only to that provider. A two-hour file takes several minutes.",
    "4. Review: click a turn, listen, fix the wording, press Ctrl+S. Name a speaker once "
    "in the left panel and every turn of theirs is renamed. Tick turns off as you check "
    "them.",
    "5. Export: Word to read and comment on, plain text to quote from, JSON with every "
    "timestamp and confidence score. Save the project first if you want to come back.")
HELP_OPEN_STEPS = (
    "1. Open project, from the sidebar or the first screen.",
    "2. Pick the .transcript.json you saved.",
    "3. Everything comes back: the text, the speaker names, your corrections, your "
    "highlights, your comments and how far you had checked.",
    "4. Press Resume to go to the turn you stopped on.",
    "5. Nothing is sent anywhere and no API credit is spent.")
HELP_OPEN_HEADING = "Come back to one you started"
HELP_SHORTCUTS_HEADING = "While reviewing"


def shortcuts(skip_seconds: int) -> tuple[str, ...]:
    """The shortcut list, with the jump length filled in from the token that sets it.

    The number lives in design_tokens.SKIP_SECONDS. Formatting it here rather than typing
    it twice is why the help could not go on claiming ten seconds after it became five.
    """
    return tuple(line.format(seconds=skip_seconds) for line in HELP_SHORTCUTS)


HELP_SHORTCUTS = ("Ctrl+S — save the correction you are typing, and the project with it.",
                  "Ctrl+Shift+S — save to a different file. Ctrl+O — open one.",
                  "Ctrl+Enter — save the correction, mark the turn reviewed, open the next "
                  "unchecked one.",
                  "Ctrl+W — play or pause. It does nothing else, anywhere, ever.",
                  "F4 does the same, for a foot pedal mapped to a function key.",
                  "Ctrl+Left / Ctrl+Right — {seconds} seconds back or forward, anywhere.",
                  "Ctrl+Up / Ctrl+Down — the previous or the next turn, anywhere.",
                  "Space and the plain arrows do the same, but only when no text field "
                  "has focus.",
                  "Ctrl+P — play the open turn from its start.",
                  "Select a phrase, then: Ctrl+B bold, Ctrl+1 / Ctrl+2 / Ctrl+3 highlight, "
                  "Ctrl+D comment on it, Ctrl+0 take the marks off.",
                  "Ctrl+M — add a comment on the whole turn, rather than on a phrase.",
                  "Ctrl+K — switch the open turn between editing and playing by word.",
                  "Ctrl+T — insert the current playback time into the text.",
                  "Ctrl+J — bring the list back to the turn you have open.",
                  "Ctrl+E — show only the turns still unchecked. Ctrl+R — resume where you "
                  "left off.",
                  "Ctrl+F — find and replace. Esc closes it.",
                  "The open turn follows the audio; the crosshair in the player stops that.")
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
# The recording screen comes before the provider is settled, so it names no service. The
# exact destination is stated on Transcription and in Settings, beside the provider picker.
QUALITY_TRANSFER = ("The original recording is never modified. A copy is prepared here and "
                    "sent to the API provider you choose; Settings names that provider and "
                    "states exactly what leaves this computer.")
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
TRANSCRIPTION_DONE = "{turns} turns transcribed"
TRANSCRIPTION_DONE_SUBTITLE = "This recording has been transcribed."
TRANSCRIPTION_DONE_BODY = ("Review it on the Speakers step. To transcribe something else, "
                           "start a new project — this one is not overwritten.")
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
SPEAKERS_TITLE = "Review"
SPEAKERS_SUBTITLE = "Give each detected voice a real name, then correct any wording."
IDENTITIES = "Speakers"
COLLAPSE_IDENTITIES = "Hide the speaker panel"
EXPAND_IDENTITIES = "Show the speaker panel"
IDENTITIES_COUNT = "{count} labels detected"
IDENTITIES_NONE = "No labels from this provider"
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
ONLY_UNCHECKED_TOOLTIP = "Hide the turns already reviewed"
ALL_CHECKED = "Nothing left unchecked here."
RESUME_TOOLTIP = "Go back to {stamp}, where you left off"
MARK_CHECKED = "Checked"
MARK_CHECKED_TOOLTIP = "Mark this turn reviewed"
SAVE_STATUS_SAVED = "Saved to {name}"
SAVE_STATUS_UNSAVED = "Unsaved changes · {name}"
SAVE_STATUS_NEW = "Not saved to a file yet"
SAVE_STATUS_UNTITLED = "No project file"
SAVE_CORRECTION_TOOLTIP = ("Ctrl+S saves it. Ctrl+Enter saves it, marks the turn reviewed "
                           "and opens the next unchecked one.")
REVIEW_DONE = "Every turn is checked."
SHOW_ORIGINAL = "Show original"
HIDE_ORIGINAL = "Hide original"
SEEK_WORDS = "Click a word to jump there"
# The two modes of the one text slot, named on a switch rather than hidden behind an icon.
MODE_EDIT = "Edit text"
MODE_WORDS = "Play by word"
# Where you are, always on screen: the hard part of a two-hour transcript is knowing that.
INSPECTOR_POSITION = "Turn {index} of {total}"
INSPECTOR_LOCATE = "Show this turn in the transcript"
NOTE_LABEL = "Comment"
NOTE_HINT = "Exported as a Word comment in the margin, never inside the transcript."
NOTE_ADD = "Add a comment (Ctrl+M)"
NOTE_PRESENT = "Comment on this turn"
SAVE_AS = "Save as…"
FILTER_CLEARED = "Showing every turn again, so this one is visible."
APPLY_NAME = "Press Enter, or click away, to apply the name"
CONTINUE_TO_EXPORT = "Continue to export"

# ── Audio player ──────────────────────────────────────────────────────────────
PLAYER_PLAY = "Play (Ctrl+W)"
PLAYER_PAUSE = "Pause (Ctrl+W)"
PLAYER_BACK = "Back {seconds} seconds"
PLAYER_FORWARD = "Forward {seconds} seconds"
FOLLOW_ON = "Following the audio — the open turn moves with it"
FOLLOW_OFF = "Follow the audio: keep the open turn on whatever is playing"

# ── Review helpers ────────────────────────────────────────────────────────────
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
SETTINGS_REVIEW = "When you pause the audio"
SETTINGS_AUTO_REWIND = "Rewind when pausing"
SETTINGS_AUTO_REWIND_SECONDS = "Rewind by (seconds)"
SETTINGS_AUTO_REWIND_HINT = "Stepping back a moment means resuming catches the start of the word."
AUDIO_MISSING_TITLE = "Audio not found. Locate the recording to enable playback."
AUDIO_MISSING_BODY = "The transcript, speakers and corrections are all loaded — only playback needs the file."
AUDIO_LOCATE = "Locate audio"
AUDIO_DISMISS = "Dismiss"
AUDIO_DIALOG_TITLE = "Locate the recording"
AUDIO_MISMATCH_TITLE = "That file does not match"
AUDIO_MISMATCH_BODY = ("The project was transcribed from {expected} ({size}). The file you chose is "
                       "{chosen} ({chosen_size}). Use it anyway?")
AUDIO_UNREADABLE = "That file could not be opened as audio."

CLOSE_INSPECTOR = "Close inspector"
INSPECTOR_TITLE = "Selected turn"
INSPECTOR_EMPTY_BODY = "Pick a turn in the transcript to read it, correct it and mark it."
INSPECTOR_EMPTY_HINT = ("Ctrl+Up and Ctrl+Down move between turns without the mouse; "
                        "Home lists every shortcut.")
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

# ── Settings screen ───────────────────────────────────────────────────────────
SETTINGS_TITLE = "Settings"
SETTINGS_SUBTITLE = "Appearance, transcription provider, and local tools."
SETTINGS_INTERFACE = "Interface"
SETTINGS_TEXT_SIZE = "Text size"
SETTINGS_APPEARANCE = "Appearance"
SHOW_WELCOME_AGAIN = "Show the introduction again"
SETTINGS_TRANSCRIPTION = "Transcription"
SETTINGS_PROVIDER = "Transcription provider"
SETTINGS_LANGUAGE = "Recording language"
SETTINGS_EXPECTED_SPEAKERS = "Expected number of speakers"
SETTINGS_EXPECTED_HINT = "Leave empty for automatic detection"
SETTINGS_ENDPOINT_URL = "Endpoint base URL"
SETTINGS_ENDPOINT_URL_HINT = "https://example.org/v1"
SETTINGS_ENDPOINT_MODEL = "Model name"
SETTINGS_ENDPOINT_MODEL_HINT = "whisper-1"
SETTINGS_ENDPOINT_PRIVACY = "The address, model, and key stay in memory only; they are never saved or exported."
SETTINGS_AUDIO = "Audio preparation"
SETTINGS_AUDIO_NOTE = "Applies to the provider that fragments the recording locally."
SETTINGS_CHUNK_LIMIT = "Fragment limit (MB)"
SETTINGS_BITRATE = "AAC fallback (kbps)"
SETTINGS_OVERLAP = "Overlap (seconds)"
SETTINGS_INCLUDE_PATH = "Include the source path in JSON"
SETTINGS_SAVE = "Save settings"
SETTINGS_FFMPEG = "FFmpeg"
SETTINGS_FFMPEG_UNAVAILABLE = "Unavailable"
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
DOC_COMMENT_AUTHOR = "Reviewer"
DOC_REVIEWER = "Reviewed by"
EXPORT_SIGNED_BY = "Comments in the Word file will be signed {name}."
EXPORT_SIGNED_NOBODY = ("Comments in the Word file will be signed “Reviewer”. "
                        "Put your name in Settings to sign them yourself.")
SETTINGS_REVIEWER = "Your name"
SETTINGS_REVIEWER_HINT = "Signs your comments in the exported Word file"
SETTINGS_REVIEWER_NOTE = ("Left blank, comments are signed “Reviewer” and the "
                          "document says nothing about who checked it.")
DOC_LEGEND = "Highlight key"
DOC_LEGEND_UNNAMED = "Colour {number}"
DOC_NOTICE = ("Note: transcription and speaker identification are automatic and require "
              "manual verification.")

# ── Controller messages that reach the activity log ───────────────────────────
LOG_FILE_ANALYSED = "File analysed."
LOG_MERGED_CHRONOLOGICALLY = "Transcript merged chronologically."
LOG_GLOBAL_SPEAKERS = "Speakers were identified across the whole recording."
LOG_FINISHED = "Transcription finished."
ERROR_ALREADY_RUNNING = "A transcription is already running."
ERROR_NO_RECORDING = "Select a valid recording first."
ERROR_METADATA_MISSING = "Recording metadata is missing."
ERROR_INCOMPATIBLE_PROJECT = "This file is not a compatible transcription project."


# --- Marking part of a turn -------------------------------------------------------------
MARK_HINT = "Select text above, then mark it."
SHORTCUT_FAILED = "That shortcut could not be carried out: {detail}"
MARK_NEEDS_SELECTION = "Select the words first, then mark them."
MARK_BOLD = "Bold"
MARK_COMMENT = "Comment on selection"
MARK_CLEAR = "Clear marks on the selection"
MARK_CLEAR_ALL = "Clear every mark on this turn"
MARK_HIGHLIGHT = "Highlight: {label}"
MARK_UNNAMED = "Colour {number}"
TURN_MARKED = "This turn carries a highlight or a comment"
MARK_PREVIEW = "As it will appear in Word"
MARK_COUNT = "{count} marked"
MARK_DETACHED = "{count} mark(s) removed: the text they were on has changed."
MARK_COMMENT_PROMPT = "Comment on “{quote}”"
SETTINGS_HIGHLIGHTS = "Highlight key"
SETTINGS_HIGHLIGHTS_HINT = ("Name each colour so a highlight means something. The names are "
                            "printed as a key in the exported Word file.")
SETTINGS_HIGHLIGHT_SLOT = "Colour {number}"


# ── Home ─────────────────────────────────────────────────────────────────────
HOME_TITLE = "Home"
HOME_SUBTITLE = "What this does, and how to get through it."
HOME_WHAT_HEADING = "What it is for"
HOME_WHAT_BODY = (
    "You give it an audio file. It sends the audio to a transcription service, gets the "
    "words back split by speaker, and puts them in front of you to correct. One "
    "interviewee or a room of twelve; twenty minutes or three hours. "
    "The recording on your disk is never touched. Your work is saved as a project file you "
    "can close and reopen. When you are finished you export a Word document with the "
    "speakers named, your highlights on the page and your comments in the margin.")
HOME_STEPS_HEADING = "The four steps"
HOME_STEPS = (
    ("Recording", "Pick the audio file. You can transcribe only part of it — set the range "
                  "here and nothing outside it is sent."),
    ("Transcription", "Press Start. The file is prepared, uploaded, and transcribed by the "
                      "provider you set in Settings. A two-hour recording takes several "
                      "minutes."),
    ("Review", "Where you spend the time. Play the audio, fix the words, name the "
               "speakers, mark the parts that matter, tick off each turn as you check it."),
    ("Export", "Word to read and comment on, plain text to quote from, JSON for analysis "
               "software. The project file keeps everything, including your marks."))
HOME_MARKING_HEADING = "Marking the text"
HOME_MARKING = (
    "Select a few words in the open turn. Then: Ctrl+B for bold, Ctrl+1, Ctrl+2 or Ctrl+3 "
    "for the three highlight colours, Ctrl+D to attach a comment to exactly those words. "
    "All of it lands in the Word file — real highlighting, real bold, comments in the "
    "margin pointing at the phrase rather than the paragraph. Name the three colours in "
    "Settings and the names are printed as a key at the top of the document.")
HOME_REVIEW_HEADING = "Keeping your place"
HOME_REVIEW = (
    "Tick a turn as checked and the counter above the transcript moves. Reopen the project "
    "and it offers to put you back on the turn you stopped at. “Show only unchecked” "
    "hides everything you have already been through.")
HOME_PRIVACY_HEADING = "What leaves this computer"
HOME_EXPORTS_HEADING = "What you can export"
HOME_EXPORTS = (
    ("Word (.docx)", "Speaker names, timestamps, your highlighting and your comments."),
    ("Plain text (.txt)", "The transcript alone, for quoting into a paper."),
    ("JSON (.json)", "Every turn with its timings, speaker and confidence, for analysis software."),
    ("Project (.transcript.json)", "Everything above plus your corrections, marks and progress."))
HOME_PROVIDERS_HEADING = "Transcription providers"
HOME_PROVIDERS_BODY = (
    "Five are supported and they do not return the same things. Some label the speakers "
    "across the whole recording, one labels them only within a fragment, one does not "
    "label speakers at all. Settings says what the one you picked will give you, before "
    "you spend anything on it.")
HOME_LANGUAGE_HEADING = "Language"
HOME_LANGUAGE_BODY = (
    "The interface is English and stays English. The language of the recording is a "
    "separate setting; it defaults to Romanian, and “Detect automatically” hands "
    "the question to the provider.")
HOME_OPEN = "Open a project"

STATUS_TURNS = "{done}/{total}"
STATUS_TURNS_TOOLTIP = "Turns marked reviewed, out of the whole transcript"
STATUS_LANGUAGE_TOOLTIP = "The language of the recording, set in Settings"

# The recording's language, offered in Settings. The interface language is not a choice:
# it is English. "auto" is not a language code — see providers/base.language_code.
LANGUAGES = (("ro", "Romanian"), ("en", "English"), ("nl", "Dutch"), ("fr", "French"),
             ("de", "German"), ("es", "Spanish"), ("it", "Italian"),
             ("auto", "Detect automatically"))


def language_name(code: str) -> str:
    """The label shown for a language code, or the code itself if it is not one of ours."""
    return dict(LANGUAGES).get(code, code or "—")


# --- Undo ---------------------------------------------------------------------------------
# Each names the act the way the person doing it would, so the toast reads as a sentence:
# "Undone: renaming Speaker 1".
UNDO = "Undo"
UNDO_TOOLTIP = "Undo {what} (Ctrl+Z)"
UNDO_EMPTY = "Nothing to undo yet"
UNDO_DONE = "Undone: {what}"
UNDO_NOTHING = "There is nothing to undo."
UNDO_RENAME = "renaming {speaker}"
UNDO_MERGE = "merging {source} into {target}"
UNDO_CORRECTION = "the correction on turn {index}"
UNDO_REASSIGN = "moving turn {index} to another speaker"
UNDO_MARK = "the marking on turn {index}"
UNDO_NOTE = "the comment on turn {index}"
UNDO_CHECKED = "checking turn {index}"
UNDO_REVIEWED = "reviewing turn {index}"
DUPLICATE_NAME = ("{name} is already the name of another speaker. If they are the same "
                  "person, merge them instead — the menu beside the name does it.")

STARTING_TOOLS = "Looking for FFmpeg…"
