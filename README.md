# TranscriptionLab

*Version 1.1.2 · English interface, transcription in Romanian by default.*

## Download

- **Windows.** Download `TranscriptionLab-Windows-v1.1.2.zip` from the
  [Releases page](../../releases/latest), unzip it anywhere and run
  `TranscriptionLab.exe`. There is no installer and no need for administrator rights.
  FFmpeg is included in the archive; nothing has to be installed separately.
- **The API key is yours to bring.** The application does not come with a transcription
  account. Choose your provider in **Settings** (Gladia, Soniox, Deepgram, OpenAI, or an
  OpenAI-compatible endpoint), then enter that provider's key on the **Transcription** step.
- **Privacy, in one line.** The recording goes only to the provider you chose, and the key
  stays in the memory of the running process: it is never written to disk, never logged and
  never exported. The sections below give the detail.

A Flet desktop application for Windows, for researchers transcribing long group interviews.
The recording is sent to a transcription provider chosen in Settings, and the result can be
reviewed and exported to DOCX, TXT and JSON. The interface is in English; the language of
the transcription is chosen separately and defaults to Romanian.

## What it does

- **Five transcription providers**, switchable in Settings: **Gladia** (the default,
  Whisper plus pyannote diarization), **Soniox**, **Deepgram**, **OpenAI**
  `gpt-4o-transcribe-diarize`, and any **OpenAI-compatible endpoint** you configure.
- **Speakers identified globally** across the whole recording with the first three
  providers: roughly as many labels as there were real participants, instead of dozens of
  labels per fragment.
- **A speaker count that genuinely binds** with Gladia (`number_of_speakers` /
  `min_speakers` / `max_speakers`); advisory with the others.
- **Capabilities declared per provider**: the interface disables what cannot be delivered
  and says in one sentence what to expect.
- **Transcribe a time range**: optionally only a portion of the recording, with timestamps
  still reported against the full original.
- **Word-level timings and confidence scores**, where the provider offers them.
- **Review tools**: global find and replace, reassigning a turn to another speaker, merging
  two speaker labels into one person, per-turn checked marks with a progress bar, a
  "show only unchecked" filter, and Resume, which reopens the project where you stopped.
- **Full provenance** in the saved project: the provider, the model and the range transcribed.
- **BYOK**: one key per provider, in process memory only.

## Providers, and what leaves the computer

Each provider receives different data. The choice is made in **Settings → Transcription**,
and the application shows the same information in the interface before transcription starts.

| Provider | What is sent | Speakers | Word timings | Confidence |
|---|---|---|---|---|
| **Gladia** (default) | a copy of the **whole** recording | global; the expected count is **enforced** on pyannote diarization | yes | yes |
| **Soniox** | a copy of the **whole** recording | global; the expected count is advisory | yes | yes |
| **Deepgram** | a copy of the **whole** recording | global; the expected count is advisory | yes | yes |
| **OpenAI** `gpt-4o-transcribe-diarize` | **only the temporary fragments** created with FFmpeg | separate for each fragment, needs manual reconciliation | no | no |
| **OpenAI-compatible endpoint** (your own) | a copy of the **whole** recording, to the address you configured | none: splitting and naming speakers is manual | only if the server returns segments | no |

Only the OpenAI path fragments the recording locally. Every other provider receives a
complete copy of the file; if that is not acceptable for your research data, use the OpenAI
provider or a compatible endpoint hosted by your own institution.

## Privacy

- The original file stays on the computer and is never modified.
- The application does not load the whole recording into memory: uploads are streamed.
- API keys stay in the memory of the running process: never saved, logged or exported. Each
  provider has its own key.
- For the OpenAI-compatible endpoint, the address and the model name likewise stay in memory only.
- Temporary files are deleted on reset and on a normal shutdown.
- The absolute path of the source is excluded from the JSON export by default; it can be
  enabled in Settings.
- The saved project records the provider and model actually used
  (`transcription_provider`, `transcription_model`), for reproducibility.

Every user supplies their own key and enables billing with the provider they chose. For
OpenAI, ChatGPT Plus and API billing are separate services: the subscription does not
include API credit.

## Supported formats

M4A, WAV, MP3, MP4, AAC, FLAC and WEBM. The fragmenting described below applies only to the
OpenAI provider; the others receive the file as it is. For compressed sources the
application tries to segment without re-encoding. Where that is not safe, and for WAV, it
encodes AAC fragments directly at mono, 16 kHz, 48 kbps, with no full intermediate WAV.

## FFmpeg, and running from source

The archive on the Releases page includes `ffmpeg.exe` and `ffprobe.exe` under
`assets\bin\windows`, so users do not have to install FFmpeg separately. The application
validates the pair and looks, in order: bundled resources, locations relative to the
executable, `PATH`, WinGet installations, and a folder the user selects.

**The binaries are not committed to this repository.** They are about 194 MB and change only
when the pinned version changes, so they are downloaded by `tools_fetch_ffmpeg.py` — that
file is the single place the version and the URL are declared. The CI workflow runs it
before every build; after a fresh clone, run it once yourself.

The build shipped is FFmpeg 8.1.2 `essentials_build` from gyan.dev. The application uses
exactly three things: `ffprobe` for stream metadata, the native AAC encoder for its compact
upload copy and its range cuts, and the MP4/M4A muxer. The essentials build carries all of
them; the full build adds external libraries this application never calls, for 268 MB of
extra download. Provenance is in `SOURCE-FFMPEG.txt`, and the licence for that build is
downloaded alongside the binaries as `LICENSE-FFMPEG.txt`. This build has GPLv3 enabled.
Anyone redistributing the application must comply with the licence and the corresponding
source obligations of the exact build they publish. Replacing either binary means updating
the provenance file and `tools_fetch_ffmpeg.py` at the same time.

Development requirements: Windows 10/11, Python 3.10–3.13, and a key for at least one of the
providers in the table above. FFmpeg can also be installed system-wide with:

```powershell
winget install --id Gyan.FFmpeg -e
```

From the project directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python tools_fetch_ffmpeg.py
flet run main.py
```

If activating the environment is blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Using it

1. In **Recording**, select the file through the native dialog and check the metadata.
   Optionally fill in **Start** and **End** (`mm:ss` or `hh:mm:ss`) to transcribe only a
   portion; left empty, the whole file is transcribed.
2. In **Transcription**, enter the key for the selected provider and start processing. The
   screen states what the chosen provider delivers. Cancelling stops the upload or the next
   API call rather than tearing down the request in flight.
3. In **Speakers**, give the labels their real names and open a turn to correct it. This is
   also where find and replace, reassigning a turn, merging two speakers and the review
   progress tools live.
4. In **Export**, fill in the metadata and save Word, TXT or JSON through the Windows dialogs.

With the providers that diarize globally (Gladia, Soniox, Deepgram) you will have roughly as
many labels as there were real participants, and the work comes down to naming them.

On the **OpenAI** path, diarized labels are created independently for each fragment:
`Speaker 1` in one fragment is not assumed to be the same person as `Speaker 1` in another,
and manual reconciliation is unavoidable.

On the **OpenAI-compatible endpoint** there are no speaker labels at all: all the text gets a
single default speaker, and separating the participants is entirely manual.

The player loads the recording once and seeks within it, so playback starts on the exact
timestamp of a turn. If the source file is missing, the project still opens — the transcript,
speakers and corrections all load, and a banner offers to locate the recording so playback
can be restored.

## Transcribing a time range

The **Start** and **End** fields on the Recording screen accept `mm:ss` or `hh:mm:ss`. An
empty Start means the beginning of the file, an empty End means its end. The application
validates the order and that both fall inside the real duration, and refuses impossible
ranges with an inline message.

When a range is set, FFmpeg extracts a sub-clip locally and **only that clip** is sent to the
provider: diarization and cost apply to the range, not to the whole recording. Timestamps in
the transcript are still reported against the **real position in the original recording**;
they do not restart from zero. The chosen range is saved in the project as
`transcription_range_start` and `transcription_range_end`, so you can report exactly which
portion was transcribed.

## Saving projects

**Save project** creates a `.transcript.json` file holding the original transcript, the
corrections, the labels, the speaker mapping, the timings, the range transcribed, the
provider and model used, the per-turn checked marks and where the review stopped — but never
the API key. **Open project** lets you carry on reviewing and exporting without transcribing
again, and Resume returns you to the turn you left off at.

Local `.transcript.json` files are ignored by Git by default, to avoid publishing research
data by accident.

## Tests

```powershell
python -m unittest discover -v
```

No test contacts a real API: every HTTP request is simulated.

## Building for Windows

The version verified in this project is Flet 0.86.1. Before a build, check the environment
and the CLI options installed:

```powershell
flet --version
flet doctor
flet build --help
```

The build itself needs the Visual Studio "Desktop development with C++" workload and
Developer Mode enabled, because `flet build windows` drives a Flutter Windows build that
uses plugin symlinks. The release workflow runs on `windows-latest`, which has both.

```powershell
python tools_fetch_ffmpeg.py
flet build windows --yes --project transcriptionlab --product "TranscriptionLab" --description "Transcribe and review long group interviews" --org org.transcriptionlab --company "TranscriptionLab" --build-version 1.1.2
```

The distribution is created in `build\windows`. Flet packages the `assets` directory into the
application, including the FFmpeg pair fetched above. Before publishing, confirm that
`ffmpeg.exe`, `ffprobe.exe`, the licence and the provenance file appear in the distribution —
the workflow checks all four.

Pass `--exclude` for anything that must not be packaged. In particular `.git` and `.flet`:
without them excluded, the entire repository history ends up inside the shipped application.

The application icon is `assets\icon.svg` (the editable source), `assets\icon.png`
(1024×1024), `assets\icon_windows.png` (what `flet build` uses for the Windows executable)
and `assets\icon.ico` (applied to the live window at runtime). After changing the SVG,
regenerate the raster files:

```powershell
python tools_make_icon.py
```

## GitHub Actions and Releases

`.github/workflows/windows-build.yml` builds the application on Windows, archives
`build\windows` and publishes the archive as an artifact. For `v*` tags it also creates a
GitHub Release and attaches the archive. The workflow runs the tests first, fetches FFmpeg,
and verifies the version, the icons and the contents of the distribution. It refuses to build
if the tag disagrees with `document_export.APP_VERSION`. No API key is needed or entered
anywhere in GitHub Actions.

Tagging a release:

```powershell
git tag -a v1.1.2 -m "TranscriptionLab 1.1.2"
git push origin v1.1.2
```

## Troubleshooting

- **FFmpeg is missing:** run `python tools_fetch_ffmpeg.py`; otherwise select a folder
  containing both executables, or install it with `winget install --id Gyan.FFmpeg -e`.
- **Invalid key:** check the key and the account permissions with the selected provider.
  Each provider has its own key field.
- **Compatible endpoint unreachable:** check the base address (without
  `/audio/transcriptions`) and the model name.
- **Quota or credit exhausted:** enable API billing; a ChatGPT subscription does not resolve
  this error.
- **Fragment too large:** lower the safe limit in Settings.
- **The source is missing after reopening a project:** the text and the export still work;
  use the banner to locate the recording and restore playback.
- **Labels differ between fragments:** this happens only on the OpenAI path. Reconcile them
  on the Speakers screen, or choose a provider with global diarization.
- **Range rejected:** check the format (`mm:ss` or `hh:mm:ss`), that Start comes before End,
  and that both fall inside the file's duration.
