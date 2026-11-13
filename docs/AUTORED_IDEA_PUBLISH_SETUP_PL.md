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

## 6. Bramka bezpieczeństwa

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
