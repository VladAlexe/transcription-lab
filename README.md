# Transcriere interviuri

Aplicație desktop Flet pentru Windows destinată cercetătorilor care transcriu interviuri de grup lungi în limba română. Înregistrările sunt analizate și fragmentate cu FFmpeg, apoi fragmentele sunt transcrise cu modelul OpenAI `gpt-4o-transcribe-diarize`. Rezultatul poate fi revizuit și exportat în DOCX, TXT și JSON.

## Confidențialitate

- Fișierul original rămâne pe calculator și nu este modificat.
- Aplicația nu încarcă în memorie întreaga înregistrare.
- Numai fragmente audio temporare sunt trimise către OpenAI.
- Cheia API rămâne exclusiv în memoria procesului: nu este salvată, jurnalizată sau exportată.
- Fișierele temporare sunt șterse la resetare și la închiderea normală.
- Calea absolută a sursei este exclusă implicit din exportul JSON; poate fi activată din Setări.

ChatGPT Plus și facturarea API OpenAI sunt servicii separate. ChatGPT Plus nu include credit API. Fiecare utilizator trebuie să furnizeze propria cheie și să activeze facturarea la `platform.openai.com`.

## Formate acceptate

M4A, WAV, MP3, MP4, AAC, FLAC și WEBM. Pentru sursele comprimate se încearcă segmentarea fără recodare. Dacă aceasta nu este sigură sau pentru WAV, aplicația encodează direct fragmente AAC mono, 16 kHz, 48 kbps, fără un WAV intermediar complet.

## FFmpeg inclus și instalare din sursă

Build-ul Windows include `ffmpeg.exe` și `ffprobe.exe` în `assets\bin\windows`, astfel încât utilizatorii unei arhive GitHub Release nu trebuie să instaleze FFmpeg separat. Aplicația validează binarele și caută, în ordine: resurse bundled, locații relative executabilului, `PATH`, instalări WinGet și folderul ales de utilizator.

Binarele incluse sunt FFmpeg 8.1.2 `full_build` distribuit de gyan.dev prin pachetul WinGet `Gyan.FFmpeg`. Proveniența este în `SOURCE-FFMPEG.txt`, iar licența livrată cu acel build este în `LICENSE-FFMPEG.txt`. Acest build are GPLv3 activat. Oricine redistribuie aplicația trebuie să respecte licența și obligațiile privind codul-sursă corespunzător ale build-ului exact distribuit. Înlocuirea binarelor impune actualizarea simultană a documentelor de proveniență și licență.

Cerințe pentru dezvoltare: Windows 10/11, Python 3.10–3.13 și acces la API-ul OpenAI. Dacă resursele bundled au fost eliminate dintr-o clonă minimală, FFmpeg poate fi instalat alternativ cu:

```powershell
winget install --id Gyan.FFmpeg -e
```

Din directorul proiectului:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
flet run main.py
```

Dacă activarea mediului este blocată:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Utilizare

1. În **Înregistrare**, selectați fișierul prin dialogul nativ și verificați metadatele.
2. În **Transcriere**, introduceți cheia API și porniți procesarea. Anularea oprește lansarea următorului apel API, fără a întrerupe brutal cererea curentă.
3. În **Vorbitori**, atribuiți nume finale etichetelor specifice fiecărui fragment și deschideți editorul unei intervenții pentru corecturi.
4. În **Export**, completați metadatele și salvați Word, TXT sau JSON prin dialogurile Windows.

Etichetele diarizate sunt create independent pentru fiecare fragment. `Speaker 1` dintr-un fragment nu este presupus automat aceeași persoană cu `Speaker 1` din alt fragment. Verificarea și reconcilierea manuală sunt obligatorii.

Butonul de redare creează la cerere un clip temporar scurt, cu aproximativ o secundă de context. Dacă sursa nu mai există, proiectul se deschide în continuare, însă redarea audio este indisponibilă.

## Salvarea proiectelor

**Salvează proiect** creează un fișier `.transcript.json` care include transcriptul original, corecțiile, etichetele, maparea vorbitorilor, timpii și referința sursei, dar niciodată cheia API. **Deschide proiect** permite continuarea revizuirii și exportului fără retranscriere.

Fișierele locale `.transcript.json` sunt ignorate implicit de Git pentru a evita publicarea accidentală a datelor de cercetare.

## Teste

```powershell
python -m unittest discover -v
python -m py_compile main.py app_controller.py app_state.py audio_processing.py transcription.py speaker_reconciliation.py document_export.py models.py theme.py utils.py
```

## Construire Windows

Versiunea verificată în acest proiect este Flet 0.86.1. Înaintea unui build, verificați mediul și opțiunile CLI instalate:

```powershell
flet --version
flet doctor
flet build --help
```

Build local confirmat de interfața CLI:

```powershell
flet build windows --yes --project transcriere-interviuri --product "Transcriere interviuri" --description "Transcriere locală a interviurilor de grup" --org ro.transcriere
```

Distribuția este creată în `build\windows`. Flet include directorul `assets` în aplicație, inclusiv perechea FFmpeg documentată. Verificați înaintea publicării că `assets\bin\windows\ffmpeg.exe`, `ffprobe.exe`, licența și proveniența apar în distribuție. Pictograma provizorie se află la `assets\icon.svg`.

Binarele mari sunt configurate pentru Git LFS. Instalați Git LFS înainte de clonare/publicare și asigurați-vă că workflow-ul descarcă obiectele LFS:

```powershell
git lfs install
git lfs pull
```

## GitHub Actions și Releases

Workflow-ul `.github/workflows/windows-build.yml` construiește aplicația pe Windows, arhivează `build\windows` și publică arhiva drept artifact. Pentru tag-uri `v*`, workflow-ul creează și un GitHub Release și atașează arhiva. Nu sunt necesare și nu sunt introduse chei OpenAI în GitHub Actions.

Exemplu de tag:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

## Depanare

- **FFmpeg lipsește:** verificați mai întâi fișierele bundled/LFS; apoi selectați un folder care conține ambele executabile sau instalați alternativ cu `winget install --id Gyan.FFmpeg -e`.
- **Cheie invalidă:** verificați cheia și permisiunile proiectului OpenAI.
- **Cotă sau credit insuficient:** activați facturarea API; abonamentul ChatGPT nu rezolvă această eroare.
- **Fragment prea mare:** reduceți limita sigură din Setări.
- **Sursa lipsește după redeschiderea proiectului:** textul și exportul funcționează, însă previzualizarea audio nu.
- **Etichete diferite între fragmente:** aceasta este o limitare normală a procesării independente; reconciliați-le în ecranul Vorbitori.
