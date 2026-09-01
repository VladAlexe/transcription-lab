# TranscriptionLab

*Versiunea 1.1.0 · interfață în limba engleză, transcriere implicit în română.*

## Descărcare

- **Windows.** Descărcați `TranscriptionLab-Windows-v1.1.0.zip` din
  [pagina Releases](../../releases/latest), dezarhivați-l oriunde și porniți
  `TranscriptionLab.exe`. Nu există instalator și nu este nevoie de drepturi de
  administrator. FFmpeg este inclus în arhivă; nu instalați nimic separat.
- **Cheia API este a dumneavoastră.** Aplicația nu vine cu un cont de transcriere.
  Alegeți furnizorul din **Settings** (Gladia, Soniox, Deepgram, OpenAI sau un endpoint
  compatibil OpenAI), apoi introduceți cheia acelui furnizor la pasul **Transcription**.
- **Confidențialitate, pe scurt.** Înregistrarea pleacă numai către furnizorul ales de
  dumneavoastră, iar cheia rămâne exclusiv în memoria procesului: nu este salvată pe disc,
  nu este jurnalizată și nu este exportată. Detalii în secțiunile de mai jos.

Aplicație desktop Flet pentru Windows destinată cercetătorilor care transcriu interviuri de grup lungi. Înregistrarea este trimisă unui furnizor de transcriere ales din Setări, iar rezultatul poate fi revizuit și exportat în DOCX, TXT și JSON. Interfața este în engleză; limba transcrierii se alege separat și este implicit româna.

## Ce face

- **Cinci furnizori de transcriere**, comutabili din Setări: **Gladia** (implicit, Whisper + diarizare pyannote), **Soniox**, **Deepgram**, **OpenAI** `gpt-4o-transcribe-diarize` și orice **endpoint compatibil OpenAI** configurat de dumneavoastră.
- **Vorbitori identificați global** pe toată înregistrarea la primii trei furnizori: aproximativ atâtea etichete câți participanți reali, în loc de zeci de etichete per fragment.
- **Număr de vorbitori impus efectiv** la Gladia (`number_of_speakers` / `min_speakers` / `max_speakers`); orientativ la ceilalți.
- **Capabilități declarate per furnizor**: interfața dezactivează ce nu poate fi livrat și spune într-o singură frază la ce să vă așteptați.
- **Transcriere pe interval**: opțional, numai o porțiune din înregistrare, cu marcaje temporale raportate la originalul complet.
- **Marcaje pe cuvinte și scor de încredere**, unde furnizorul le oferă.
- **Proveniență completă** în proiectul salvat: furnizorul, modelul și intervalul transcris.
- **BYOK**: câte o cheie per furnizor, exclusiv în memoria procesului.

## Furnizori și ce părăsește calculatorul

Fiecare furnizor primește date diferite. Alegerea se face din **Setări → Transcriere**, iar aplicația afișează aceeași informație și în interfață, înaintea pornirii transcrierii.

| Furnizor | Ce este trimis | Vorbitori | Marcaje pe cuvinte | Încredere |
|---|---|---|---|---|
| **Gladia** (implicit) | o copie a **întregii** înregistrări | globali, numărul estimat este **impus** diarizării pyannote | da | da |
| **Soniox** | o copie a **întregii** înregistrări | globali, numărul estimat este orientativ | da | da |
| **Deepgram** | o copie a **întregii** înregistrări | globali, numărul estimat este orientativ | da | da |
| **OpenAI** `gpt-4o-transcribe-diarize` | **numai fragmentele temporare** create cu FFmpeg | separați pentru fiecare fragment, necesită reconciliere manuală | nu | nu |
| **Endpoint compatibil OpenAI** (propriu) | o copie a **întregii** înregistrări, către adresa configurată de dumneavoastră | niciunul: delimitarea și denumirea vorbitorilor sunt manuale | doar dacă serverul returnează segmente | nu |

Numai calea OpenAI fragmentează local înregistrarea. Toți ceilalți furnizori primesc o copie completă a fișierului; dacă acest lucru nu este acceptabil pentru datele dumneavoastră de cercetare, folosiți furnizorul OpenAI sau un endpoint compatibil găzduit de instituția dumneavoastră.

## Confidențialitate

- Fișierul original rămâne pe calculator și nu este modificat.
- Aplicația nu încarcă în memorie întreaga înregistrare: încărcarea se face în flux.
- Cheile API rămân exclusiv în memoria procesului: nu sunt salvate, jurnalizate sau exportate. Fiecare furnizor are propria cheie.
- Pentru endpoint-ul compatibil OpenAI, adresa și numele modelului rămân de asemenea doar în memorie.
- Fișierele temporare sunt șterse la resetare și la închiderea normală.
- Calea absolută a sursei este exclusă implicit din exportul JSON; poate fi activată din Setări.
- Proiectul salvat înregistrează furnizorul și modelul folosite efectiv (`transcription_provider`, `transcription_model`), pentru reproductibilitate.

Fiecare utilizator își furnizează propria cheie și activează facturarea la furnizorul ales. Pentru OpenAI, ChatGPT Plus și facturarea API sunt servicii separate: abonamentul nu include credit API.

## Formate acceptate

M4A, WAV, MP3, MP4, AAC, FLAC și WEBM. Fragmentarea descrisă mai jos se aplică numai furnizorului OpenAI; ceilalți primesc fișierul așa cum este. Pentru sursele comprimate se încearcă segmentarea fără recodare. Dacă aceasta nu este sigură sau pentru WAV, aplicația encodează direct fragmente AAC mono, 16 kHz, 48 kbps, fără un WAV intermediar complet.

## FFmpeg inclus și instalare din sursă

Arhiva de pe Releases include `ffmpeg.exe` și `ffprobe.exe` în `assets\bin\windows`, astfel încât utilizatorii nu trebuie să instaleze FFmpeg separat. Aplicația validează binarele și caută, în ordine: resurse bundled, locații relative executabilului, `PATH`, instalări WinGet și folderul ales de utilizator.

**Binarele nu sunt urcate în depozit.** Sunt ~194 MB și se schimbă doar când se schimbă versiunea fixată, așa că sunt descărcate de `tools_fetch_ffmpeg.py` — acel fișier este singurul loc unde versiunea și adresa sunt declarate. Fluxul de build din CI îl rulează înainte de fiecare compilare; la o clonă nouă, rulați-l o dată dumneavoastră.

Build-ul distribuit este FFmpeg 8.1.2 `essentials_build` de la gyan.dev. Aplicația folosește exact trei lucruri: `ffprobe` pentru metadate, codorul AAC nativ pentru copia compactă de încărcare și pentru decupajele pe interval, și muxer-ul MP4/M4A. Toate există în `essentials`; `full_build` adaugă biblioteci externe pe care aplicația nu le apelează, contra 268 MB descărcați în plus. Proveniența este în `SOURCE-FFMPEG.txt`, iar licența build-ului este descărcată alături de binare în `LICENSE-FFMPEG.txt`. Acest build are GPLv3 activat. Oricine redistribuie aplicația trebuie să respecte licența și obligațiile privind codul-sursă corespunzător ale build-ului exact distribuit. Înlocuirea binarelor impune actualizarea simultană a documentelor de proveniență și licență.

Cerințe pentru dezvoltare: Windows 10/11, Python 3.10–3.13 și o cheie pentru cel puțin unul dintre furnizorii din tabelul de mai sus. Alternativ, FFmpeg poate fi instalat în sistem cu:

```powershell
winget install --id Gyan.FFmpeg -e
```

Din directorul proiectului:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python tools_fetch_ffmpeg.py
flet run main.py
```

Dacă activarea mediului este blocată:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Utilizare

1. În **Recording**, selectați fișierul prin dialogul nativ și verificați metadatele. Opțional, completați **Start** și **End** (`mm:ss` sau `hh:mm:ss`) pentru a transcrie numai o porțiune; lăsate goale, se transcrie tot fișierul.
2. În **Transcription**, introduceți cheia furnizorului selectat și porniți procesarea. Ecranul afișează ce livrează furnizorul ales. Anularea oprește încărcarea sau lansarea următorului apel API, fără a întrerupe brutal cererea curentă.
3. În **Speakers**, atribuiți nume finale etichetelor și deschideți editorul unei intervenții pentru corecturi.
4. În **Export**, completați metadatele și salvați Word, TXT sau JSON prin dialogurile Windows.

Cu furnizorii care diarizează global (Gladia, Soniox, Deepgram) veți avea aproximativ atâtea etichete câți participanți reali există, iar munca se rezumă la atribuirea numelor.

Pe calea **OpenAI**, etichetele diarizate sunt create independent pentru fiecare fragment: `Speaker 1` dintr-un fragment nu este presupus automat aceeași persoană cu `Speaker 1` din alt fragment, iar reconcilierea manuală este obligatorie.

Pe **endpoint-ul compatibil OpenAI** nu există deloc etichete de vorbitor: tot textul primește un singur vorbitor implicit, iar delimitarea participanților rămâne integral manuală.

Butonul de redare creează la cerere un clip temporar scurt, cu aproximativ o secundă de context. Dacă sursa nu mai există, proiectul se deschide în continuare, însă redarea audio este indisponibilă.

## Transcrierea unui interval

Câmpurile **Start** și **End** de pe ecranul Recording acceptă `mm:ss` sau `hh:mm:ss`. Start gol înseamnă începutul fișierului, End gol înseamnă sfârșitul lui. Aplicația validează ordinea și încadrarea în durata reală și refuză intervalele imposibile cu un mesaj inline.

Când un interval este setat, FFmpeg extrage local un sub-clip și **numai acel clip** este trimis furnizorului: diarizarea și costul se aplică intervalului, nu întregii înregistrări. Marcajele temporale din transcript rămân raportate la **poziția reală în înregistrarea originală**, nu repornesc de la zero. Intervalul ales este salvat în proiect ca `transcription_range_start` și `transcription_range_end`, ca să puteți raporta exact ce porțiune a fost transcrisă.

## Salvarea proiectelor

**Save project** creează un fișier `.transcript.json` care include transcriptul original, corecțiile, etichetele, maparea vorbitorilor, timpii, intervalul transcris, furnizorul și modelul folosite, dar niciodată cheia API. **Open project** permite continuarea revizuirii și exportului fără retranscriere.

Fișierele locale `.transcript.json` sunt ignorate implicit de Git pentru a evita publicarea accidentală a datelor de cercetare.

## Teste

```powershell
python -m unittest discover -v
```

Niciun test nu contactează un API real: toate cererile HTTP sunt simulate.

## Construire Windows

Versiunea verificată în acest proiect este Flet 0.86.1. Înaintea unui build, verificați mediul și opțiunile CLI instalate:

```powershell
flet --version
flet doctor
flet build --help
```

Build local confirmat de interfața CLI:

```powershell
flet build windows --yes --project transcriptionlab --product "TranscriptionLab" --description "Transcribe and review long group interviews" --org org.transcriptionlab --company "TranscriptionLab" --build-version 1.1.0
```

Distribuția este creată în `build\windows`. Flet include directorul `assets` în aplicație, inclusiv perechea FFmpeg documentată. Verificați înaintea publicării că `assets\bin\windows\ffmpeg.exe`, `ffprobe.exe`, licența și proveniența apar în distribuție.

Pictograma aplicației este `assets\icon.svg` (sursa editabilă) și `assets\icon.png` (1024×1024, folosită de `flet build`). După orice modificare a formei SVG, regenerați PNG-ul:

```powershell
python tools_make_icon.py
```

Binarele mari sunt configurate pentru Git LFS. Instalați Git LFS înainte de clonare/publicare și asigurați-vă că workflow-ul descarcă obiectele LFS:

```powershell
git lfs install
git lfs pull
```

## GitHub Actions și Releases

Workflow-ul `.github/workflows/windows-build.yml` construiește aplicația pe Windows, arhivează `build\windows` și publică arhiva drept artifact. Pentru tag-uri `v*`, workflow-ul creează și un GitHub Release și atașează arhiva. Workflow-ul rulează întâi testele și verifică prezența pictogramei și a binarelor FFmpeg. Nicio cheie API nu este necesară sau introdusă în GitHub Actions.

Exemplu de tag:

```powershell
git tag v1.1.0
git push origin v1.1.0
```

## Depanare

- **FFmpeg lipsește:** verificați mai întâi fișierele bundled/LFS; apoi selectați un folder care conține ambele executabile sau instalați alternativ cu `winget install --id Gyan.FFmpeg -e`.
- **Cheie invalidă:** verificați cheia și permisiunile contului la furnizorul selectat. Fiecare furnizor are propriul câmp de cheie.
- **Endpoint compatibil inaccesibil:** verificați adresa de bază (fără `/audio/transcriptions`) și numele modelului.
- **Cotă sau credit insuficient:** activați facturarea API; abonamentul ChatGPT nu rezolvă această eroare.
- **Fragment prea mare:** reduceți limita sigură din Setări.
- **Sursa lipsește după redeschiderea proiectului:** textul și exportul funcționează, însă previzualizarea audio nu.
- **Etichete diferite între fragmente:** apare numai pe calea OpenAI; reconciliați-le în ecranul Speakers sau alegeți un furnizor cu diarizare globală.
- **Interval respins:** verificați formatul (`mm:ss` sau `hh:mm:ss`), ordinea Start < End și încadrarea în durata fișierului.
