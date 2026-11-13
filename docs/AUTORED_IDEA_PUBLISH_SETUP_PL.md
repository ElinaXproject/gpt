# AUTORED IDEA — bezpieczne uruchomienie integracji Publora

## Cel
Ten dokument opisuje jedyne ręczne czynności wymagane do uruchomienia bezpiecznego testu integracji. Workflow preflight jest wyłącznie odczytowy: sprawdza połączenia i tokeny, nie tworzy szkiców, nie planuje i nie publikuje.

## 1. Wymagany sekret API
1. Zaloguj się do własnego konta Publora i utwórz klucz API w sekcji API.
2. Nie wklejaj klucza do rozmowy, kodu, pliku JSON, issue ani logów.
3. W repozytorium GitHub `ElinaXproject/gpt` otwórz Settings → Secrets and variables → Actions → New repository secret.
4. Nazwa sekretu musi być dokładnie `PUBLORA_API_KEY`.
5. Wartością jest klucz utworzony w Publora.

Dodatkowo utwórz Cloudflare API Token z minimalnym uprawnieniem D1 do odczytu/zapisu bazy `autored_idea_db` (wymagane do rejestracji statusów publikacji i eksportu backupu) i zapisz go jako GitHub Actions secret `CLOUDFLARE_API_TOKEN`. Nie używaj Global API Key.

Klient AUTORED IDEA odczytuje klucz wyłącznie ze zmiennej środowiskowej. Nie ma klucza zapisanego w repozytorium ani w Cloudflare Workerze.

## 2. Połączenia kont
W dashboardzie Publora połącz przez oficjalny OAuth trzy konta docelowe:
- TikTok `@pieknemedia` — obecnie połączone i aktywne.
- TikTok `@ocenionona6` — obecnie brak połączenia w Publora.
- YouTube `@MemoryAgent-r3c` — obecnie brak potwierdzonego połączenia w Publora.

Dla YouTube wymagany jest dokładny kanał:
- vidIQ potwierdza handle `@memoryagent-r3c` i channel ID `UCOE1EX9WZGDesaJNYIEhj7g`.
- Połączenie Metricool zwraca inny ID `UCRmmEQysOmUbs8mpZEOgtLw`; nie używać go jako celu publikacji.

## 3. Test tylko do odczytu
Po dodaniu sekretu i połączeniu kont:
1. Otwórz GitHub → Actions.
2. Wybierz workflow `AUTORED IDEA Publora preflight`.
3. Uruchom `Run workflow`.

Workflow:
- odczyta listę połączeń,
- sprawdzi mapowanie trzech profili w D1,
- sprawdzi dokładne uchwyty i stan połączeń,
- sprawdzi YouTube channel ID,
- odczyta plan, dozwolone platformy, pozostały limit miesięczny, wolne sloty kolejki i horyzont planowania,
- nie utworzy posta i nie wykona publikacji.

Wymagany wynik: `status: ready`, `ready_profiles: 3`.

## 4. Limity darmowego planu
Aktualny snapshot Publora Starter: 15 platform-postów miesięcznie łącznie, 3 aktywne sloty kolejki, horyzont 7 dni. Limit jest niewystarczający do codziennej publikacji na trzech profilach. Publora pozostaje adapterem testowym/fallbackiem; nie wolno obchodzić limitów ani aktywować planu płatnego.

## 5. Natywne API — docelowa ścieżka bez limitu Publora

### TikTok
- Wymagane: oficjalna aplikacja Content Posting API, OAuth każdego właściciela konta i scope `video.publish`.
- Publiczne Direct Post wymaga oficjalnego audytu aplikacji TikTok. Nieaudytowana aplikacja w adapterze AUTORED może używać wyłącznie `SELF_ONLY`; kod blokuje publikację publiczną.
- Adapter sprawdza konto twórcy, dostępne ustawienia prywatności, limit długości filmu, termin publikacji i licencjonowany dźwięk osadzony w pliku.
- Wymagane sekrety GitHub Actions: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_PIEKNEMEDIA_REFRESH_TOKEN`, `TIKTOK_OCENIONONA6_REFRESH_TOKEN`, `AUTORED_TOKEN_ENCRYPTION_KEY`.
- `TIKTOK_APP_AUDITED=true` wolno ustawić wyłącznie po rzeczywistym zatwierdzeniu aplikacji przez TikTok. Domyślnie pozostaje false.

### YouTube
- Wymagane: Google OAuth z zakresami `youtube.upload` i `youtube.readonly`, autoryzacja dokładnego kanału `@MemoryAgent-r3c` i channel ID `UCOE1EX9WZGDesaJNYIEhj7g`.
- Adapter sprawdza channel ID przed uploadem, używa resumable upload i planuje publikację przez `status.publishAt`.
- Publiczny upload jest zablokowany, dopóki projekt API nie przejdzie wymaganego audytu/verification. `YOUTUBE_API_AUDITED=true` wolno ustawić wyłącznie po oficjalnym zatwierdzeniu.
- Wymagane sekrety: `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`.

### Tokeny i bezpieczeństwo
- Refresh tokeny TikTok po pierwszym użyciu są przechowywane w D1 jako AES-256-GCM ciphertext; klucz `AUTORED_TOKEN_ENCRYPTION_KEY` to Base64 z 32 losowych bajtów.
- Klucz generuje się lokalnie: `python -c "import secrets,base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"`.
- Nie wklejaj tokenów ani kluczy do rozmowy, repozytorium, issue lub logów.
- Jeżeli regulamin platformy wymaga pełnoletniego właściciela aplikacji lub dodatkowej zgody, konfigurację wykonuje uprawniony dorosły właściciel. System nie obchodzi limitów wieku, audytu, OAuth ani weryfikacji.

## 5A. Automatyczny dispatcher kolejki

- Workflow `.github/workflows/publisher-dispatch.yml` sprawdza kolejkę co 15 minut i można go uruchomić ręcznie.
- Działa tylko po dodaniu sekretu `CLOUDFLARE_API_TOKEN`; brak sekretu powoduje bezpieczne pominięcie przebiegu.
- Repozytorium jest publiczne: workflow pobiera wyłącznie pojedynczy artefakt `media_bundle.zip.age` po numerycznym ID; jawne pliki manifestu lub MP4 są odrzucane. Pakiet odszyfrowuje się lokalnie w runnerze i weryfikuje manifest względem D1 (content_id, profile_id, harmonogram i idempotency key), a następnie uruchamia właściwy adapter.
- Uprawnienia workflow są ograniczone do odczytu repozytorium i artefaktów. Nie publikuje, jeśli brakuje poświadczeń providera, nie przechodzi walidacja manifestu/mediów lub nie ma praw do publikacji.
- Ręczne uruchomienie ma opcję `dry_run`, która tylko wyświetla kwalifikujące się zadania.
- Wymagane sekrety: `CLOUDFLARE_API_TOKEN`, `AUTORED_ARTIFACT_AGE_IDENTITY`, `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_PIEKNEMEDIA_REFRESH_TOKEN`, `TIKTOK_OCENIONONA6_REFRESH_TOKEN`, `AUTORED_TOKEN_ENCRYPTION_KEY`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`. Nie wklejaj ich do rozmowy ani repozytorium.
- Zmienne audytu `TIKTOK_APP_AUDITED` i `YOUTUBE_API_AUDITED` pozostają domyślnie false; ustawienie true jest dopuszczalne wyłącznie po rzeczywistym zatwierdzeniu odpowiedniej aplikacji przez platformę.
- Kod i testy dispatcher: `scripts/publisher_dispatch.py`, `tests/test_publisher_dispatch.py`. Nie wykonano jeszcze produkcyjnego dispatchu, ponieważ D1 ma 0 zadań i 0 tokenów.

### Klucz szyfrowania artefaktów mediów

1. Uprawniony właściciel generuje osobną parę age lokalnie: `age-keygen -o autored-media-key.txt`.
2. Publiczny recipient zapisuje jako GitHub Actions repository variable `AUTORED_ARTIFACT_AGE_RECIPIENT`.
3. Prywatną tożsamość (zawartość pliku age identity) zapisuje jako GitHub Actions repository secret `AUTORED_ARTIFACT_AGE_IDENTITY`. Nie wkleja jej do rozmowy ani repozytorium.
4. Przed uploadem artefaktu uruchamia `python scripts/create_media_artifact.py --manifest manifest.json --media final.mp4 --output media_bundle.zip.age` i publikuje wyłącznie plik `media_bundle.zip.age`.
5. Nigdy nie uploadować do publicznego repozytorium surowego `manifest.json`, `.mp4` ani plaintext ZIP. Brak recipienta lub identity blokuje proces.

### Render → encrypted artifact → D1 queue

1. Dla istniejącego draftu utwórz wejście renderera: `python scripts/build_render_input.py --content-id ID --profile-id PROFILE --output render-input.json`.
2. Wygeneruj MP4 przez `scripts/render_vertical_video.py` (wymaga FFmpeg/Piper i zasobów głosu/tła). Dla TikToka renderer wymaga osadzonego, licencjonowanego audio.
3. Wykonaj safety review, a dla profili faktograficznych także human fact-check. Bez tych raportów manifest nie powstanie.
4. W workflow renderującym wywołaj composite action `.github/actions/package-and-schedule` po wygenerowaniu MP4. Wymagane: `CLOUDFLARE_API_TOKEN`, repository variable `AUTORED_ARTIFACT_AGE_RECIPIENT`, uprawnienia `actions: write` i `contents: read`.
5. Przekaż do action: `content-id`, `profile-id`, `provider`, `media-path`, `scheduled-at`. Dla YouTube wymagane jest jawne `audience-classification`; dla TikToka `music-embedded=true` i `music-license-reference`.
6. Action sama przyłącza metadane mediów, tworzy provider manifest, szyfruje bundle, uploaduje wyłącznie zaszyfrowany artefakt i zapisuje job w D1. Dispatcher sprawdza kolejkę co 15 minut.

### Human safety-review gate

- Każdy content musi przejść osobną checklistę: `content_safety`, `copyright_rights`, `platform_rules`, `ai_disclosure`; TikTok wymaga także `music_license`, a profile faktograficzne `factual_accuracy`.
- Po obejrzeniu finalnego tekstu, obrazu/wideo, audio, praw/licencji i disclosure, uprawniony recenzent przygotowuje JSON z `reviewer`, `reviewed_at` (timezone), `decision` oraz booleanami `checks` i uruchamia: `python scripts/submit_safety_review.py --content-id ID --profile-id PROFILE --report safety-review.json`.
- Każdy fałsz lub brak wymaganej kontroli zapisuje status `blocked`; tylko komplet pozytywnych kontroli zapisuje `passed`. Publisher ponownie sprawdza raport i referencję SHA-256.
- Safety review i fact-check to dwa niezależne gate'y. Jeden nie zastępuje drugiego.

### Human fact-check gate dla treści faktograficznych

- Dla profilu YouTube każdy claim musi mieć bezpośrednie wsparcie z co najmniej dwóch niezależnych, allowlistowanych domen; dla profilu edukacyjnego TikTok wymagane jest co najmniej jedno źródło. Wszystkie źródła muszą mieścić się w oknie 72 godzin.
- Raport musi zawierać `profile_key`, `reviewed_at` z timezone, `reviewer`, `reviewer_type: "human"`, `decision: "approved"`, listę `claims` oraz `evidence` z URL, tytułem, datą i identyfikatorami wspieranych claims.
- Po rzeczywistym przeczytaniu źródeł i sprawdzeniu każdego twierdzenia uprawniony recenzent uruchamia: `python scripts/submit_factcheck.py --content-id ID --profile-id PROFILE --report factcheck.json`.
- CLI waliduje raport i zapisuje jego JSON, źródła oraz kryptograficzną referencję w D1. Publisher ponownie waliduje raport przy rezerwacji zadania. Raport AI nie zastępuje ludzkiego zatwierdzenia.
- Ten gate nie zastępuje osobnego `safety_review_status=passed` ani kontroli praw do mediów.

## 6. Bramka bezpieczeństwa

- Publikacja może odbywać się wyłącznie z kont, których właściciele spełniają aktualne wymagania wieku i kwalifikacji danej platformy. Nie wolno fałszować wieku, obchodzić kontroli tożsamości ani omijać wymaganej zgody lub nadzoru osoby dorosłej.


## 6. Bramka bezpieczeństwa
Do czasu przejścia preflight:
- nie uruchamiać automatycznej publikacji,
- nie używać Metricool dla YouTube,
- nie tworzyć postów testowych na profilach publicznych,
- nie ustawiać flag audytu na true bez oficjalnej decyzji platformy,
- nie umieszczać sekretów w repozytorium,
- nie omijać limitów, OAuth, audytu ani zasad platform.

Źródła techniczne:
- https://docs.publora.com/getting-started
- https://docs.publora.com/endpoints/platform-connections
- https://docs.publora.com/endpoints/create-post
- https://docs.publora.com/endpoints/upload-media
