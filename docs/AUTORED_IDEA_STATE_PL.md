# AUTORED IDEA — stan realizacji

**Aktualizacja:** 2026-11-13 17:12 Europe/Warsaw  
**Repozytorium:** https://github.com/ElinaXproject/gpt  
**Gałąź:** main  
**Ogólny status:** IN PROGRESS — brak gotowości produkcyjnej

## Postęp

| Obszar | Status | Dowód |
|---|---|---|
| Audyt bazowy | VERIFIED | odczyty GitHub, Activepieces, Publora, Metricool i Cloudflare |
| Architektura | DONE | Cloudflare Worker + D1 + Workers AI, GitHub Actions/FFmpeg |
| Plan etapów | DONE | roadmapa etapów 0–12 |
| Bezpieczeństwo i DR | DONE (projekt) | plan zabezpieczeń, backupu, retencji, RPO/RTO i napraw |
| Plan testów | DONE (projekt) | macierz T01–T22 plus kontrole wdrożenia |
| Core Python | VERIFIED | profile, walidacja pakietu, idempotencja, maszyna stanów, limity, retry, fresh-source gates i fact-check report; CI PASS |
| CI GitHub | VERIFIED | workflow #116–#125: regresja, testy core, składnia Workera, harmonogram, health wdrożonego Workera oraz testy RSS PASS |
| Cloudflare D1 | VERIFIED | baza EU/EEUR, tabele, indeksy i 3 profile sprawdzone zapytaniami SQL |
| Cloudflare Worker | DEPLOYED / CODE AHEAD | deployed version `77cfcc3edf90412799c81eceb2cb7bce` has health + read-only `/ideas`; current repository source additionally generates one safe humor draft per day with `safety_review_status=pending`; CI #215 PASS, latest draft-generation source still awaits deployment |
| Cron | CONFIGURED | dwa wywołania UTC z kontrolą 09:00 Europe/Warsaw i DST |
| Workers AI | PARTIAL | prosty JSON i FLUX image smoke test przeszły; pełny batch 3 profili oraz integracja assetów niezweryfikowane |
| Pierwszy przebieg Cron | NOT RUN | oczekuje na następne lokalne 09:00 |
| Zapis pomysłów w D1 | NOT RUN | tabela jest gotowa, brak jeszcze rekordów z Cron |
| Research i weryfikacja źródeł | PARTIAL | 9/9 RSS PASS; 72h digest z dopasowaniem tematów działa i zapisuje artefakt; fact-check nadal ręczny/niezautomatyzowany |
| Kalendarz i strategie profili | PARTIAL | profile zarejestrowane; dedykowane kalendarze i reguły nieukończone |
| Renderowanie mediów | PARTIAL | Piper + FFmpeg H.264/AAC; ffprobe validators for TikTok 9:16 and YouTube vertical/landscape; artifact handoff and production manifest integration pending |
| TikTok @pieknemedia | PARTIAL | Publora active, limit 15 postów/mies.; bezpieczny klient API i testy gotowe; brak klucza API w środowisku wykonawczym |
| TikTok @ocenionona6 | BLOCKED | Metricool połączony; brak potwierdzonego limitu planu i brak backendowego tokenu/adaptera; brak połączenia w Publora |
| YouTube @MemoryAgent-r3c | BLOCKED | Metricool ID nie zgadza się z ID vidIQ; brak poprawnego połączenia i backendowego tokenu/adaptera |
| Publikacja E2E | BLOCKED | klient Publora i pipeline zapisujący job do D1 mają testy CI PASS; brak API secrets i dwóch połączeń kont; żadna publikacja nie została wykonana |
| Backup / restore | BLOCKED | plan istnieje, brak odseparowanego magazynu i testu odtworzenia |

## Kontrola produkcyjnej bazy D1 — 2026-11-13 21:03 Europe/Warsaw

- Odczytano bez modyfikacji produkcyjną bazę `autored_idea_db` w regionie EEUR.
- Profile: dokładnie 3 rekordy, wszystkie `enabled=1`: TikTok `@pieknemedia`, TikTok `@ocenionona6`, YouTube `@MemoryAgent-r3c`.
- `content_items`: 0 rekordów; `publication_jobs`: 0 rekordów; `daily_runs`: 0 rekordów; `provider_tokens`: 0 rekordów.
- Wniosek: schema i mapowanie profili są wdrożone, ale pierwszy przebieg Cron nie utworzył jeszcze treści; nie ma aktywnej autoryzacji tokenowej w D1 i nie ma zadań gotowych do publikacji.
- Dodatkowo oba publish runnery obliczają SHA-256 mediów strumieniowo w blokach 8 MiB zamiast ładować cały plik do pamięci; testy hash helpera przechodzą w CI #279.

## Zasoby wdrożone

- Cloudflare Worker: `autored-idea-api`.
- Cloudflare D1: `autored_idea_db`, EU jurisdiction, region EEUR.
- Workers AI binding: `AI`; kod Workera jawnie wywołuje model `@cf/meta/llama-3.1-8b-instruct`.
- D1 binding: `DB`.
- Cron: `0 7,8 * * *` UTC; kod filtruje wywołanie do 09:00 czasu polskiego.
- KV i R2 nie są używane.
- Endpoint health jest skonfigurowany, ale zewnętrzny odczyt nie został potwierdzony w tym środowisku.
- Szczegóły i dowody: `docs/AUTORED_IDEA_DEPLOYMENT_2026-11-13_PL.md`.

## Zmiany wykonane

- Dodano architekturę, decyzje, plan etapów, bezpieczeństwo/DR, macierz testów i audyt bazowy.
- Dodano core Python i testy idempotencji, stanów, limitów i walidacji.
- Dodano Cloudflare Worker z harmonogramem, walidacją odpowiedzi JSON, filtrem bezpieczeństwa i deterministycznym zapisem pomysłów.
- Dodano obowiązkowy safety review w core i D1; pakiet bez pozytywnej kontroli nie przejdzie walidacji publikacji.
- Dodano renderer Piper/FFmpeg, licencjonowany polski głos, napisy, format 9:16 i kontrolę muzyki na podstawie licencji.
- Smoke test renderera potwierdził H.264 1080×1920 i AAC 48 kHz stereo; próbka poprawnie renderuje polskie znaki.
- Utworzono D1, tabele, indeksy i mapowanie trzech profili.
- Włączono Worker, D1 i AI binding; ustawiono Cron.
- Dodano migrację D1 do repozytorium.
- CI potwierdziło testy regresyjne, składnię modułu Workera, testy harmonogramu i health przed ostatnim wdrożeniem.
- Dodano atomowy claim dziennego uruchomienia Cron oraz odzyskiwanie wygasłej blokady po awarii; nowe testy aktywnej i przeterminowanej blokady przeszły w GitHub Actions #117/#118.
- Wdrożono tę poprawkę do Cloudflare jako wersję `8660ea00-5763-47ce-974b-f54b89f69cfa`, 100% ruchu; zachowano istniejące bindingi D1/AI i harmonogram Cron.
- Odczyt Cloudflare API potwierdził wersję, bindingi i harmonogram po wdrożeniu; GitHub Actions #125 potwierdził HTTP health 200 po wdrożeniu.
- Smoke test RSS potwierdził 9/9 feedów; poprawiono walidację hostów i osobną allowlistę endpointów RSS.
- Dodano generator research digest z oknem 72h, kontrolą domen i dat, dopasowaniem tytułów do zapytań oraz wyraźnym oznaczeniem braku źródeł. Smoke workflow #5: PASS, artefakt `autored-research-digest-smoke` utworzony.
- Dodano read-only endpoint Worker `/ideas?date=YYYY-MM-DD`; zwraca wyłącznie pola potrzebne researchowi, nie udostępnia opisów, praw ani sekretów. Wdrożono wersję `77cfcc3edf90412799c81eceb2cb7bce`; CI #164 potwierdził health i walidację endpointu.
- Dodano walidator raportów fact-check: niezależne domeny, bezpośrednie mapowanie dowodów do twierdzeń, allowlista, daty w oknie 72h i hash raportu. CI #168: PASS; walidator nie zastępuje semantycznej oceny prawdziwości.
- Worker source generuje teraz oryginalny szkic humorystyczny dla `@pieknemedia`: 3–5 scen, 20–45 sekund, metadane i voiceover; deterministyczny filtr bezpieczeństwa blokuje część niedozwolonych treści. Zapis ustawia `safety_review_status='pending'`, więc szkic nie przejdzie do publikacji bez osobnego zatwierdzenia. CI #215: 98 Python tests + 13 Worker tests PASS; kod wymaga jeszcze deploymentu.
- Zweryfikowano D1 Time Travel: baza produkcyjna ma backend `production`, EU/EEUR; bookmark bieżący i historyczny działają. Test restore na odizolowanej bazie testowej przywrócił stan sprzed dodatkowego rekordu; baza testowa została usunięta.
- R2 pozostaje wyłączony (Cloudflare API wymaga ręcznego włączenia w Dashboard). Przygotowano workflow szyfrowanego backupu D1 do GitHub Artifacts na 90 dni oraz lokalny weryfikator odszyfrowania, SHA-256 i SQLite integrity; wymaga `CLOUDFLARE_API_TOKEN` i `BACKUP_AGE_RECIPIENT`.
- Dodano codzienny workflow research o 09:15 czasu Europe/Warsaw z obsługą DST i retencją artefaktu 3 dni; workflow YAML został przyjęty przez GitHub Actions, pierwszy harmonogram jeszcze nie wykonał się.
- Dodano klienta Publora po stronie serwera: dokładne mapowanie uchwytu, kontrola stanu połączenia, tworzenie szkicu, upload mediów, planowanie UTC, limit 7 dni, account-context quota gate i idempotency key. CI PASS. Nie wykonano żadnej publikacji.
- Dodano natywny TikTok Direct Post adapter z refresh-token rotation, D1 AES-GCM vault, sprawdzeniem właściciela konta, ograniczeniem publicznego postowania do aplikacji po audycie, due-time gate i wymogiem osadzonej licencjonowanej ścieżki audio.
- Dodano natywny YouTube uploader: OAuth refresh, weryfikacja dokładnego channel ID `UCOE1EX9WZGDesaJNYIEhj7g`, resumable upload, `publishAt` oraz bramka oficjalnego audytu dla publicznego planowania.
- Dodano `scripts/tiktok_publish.py` i `scripts/youtube_publish.py`, walidatory FFprobe dla TikTok/YouTube oraz pola D1 dla fact-check, licencji muzyki, providerów i artefaktów.
- Dodano tabelę D1 `provider_tokens` i AES-256-GCM token vault; rotowane tokeny TikTok są szyfrowane w D1.
- Testy CI #248–#251: PASS; ostatni raport obejmuje 121 testów Python oraz testy Worker. Brak publikacji publicznej; OAuth, oficjalne audyty, media artifact scheduler i niezależna akceptacja safety pozostają blokadami.
- Dodano D1 publication job adapter: sprawdza content_id/profile/status, zapisuje idempotentny job `planned`, aktualizuje content item do `scheduled`; pipeline wymaga Cloudflare D1 tokenu, nie publikuje bez rejestracji joba. Testy D1 adaptera i integracji Publora w CI #192/#194: PASS.
- TikTok Direct Post: poprawiono transfer zgodnie z aktualnym oficjalnym Media Transfer Guide — limit pliku 4 GB, limit uploadu 10 min, prawidłowy plan chunków (poniżej 5 MB jeden upload, do 64 MB jeden chunk, powyżej 64 MB sekwencja bloków 5–64 MB z dołączeniem końcowych bajtów do ostatniego bloku), `total_chunk_count=floor` i wymagane kody odpowiedzi 206/201. Rozszerzono allowlistę o udokumentowane regionalne hosty `upload.<region>.tiktokapis.com`. GitHub Actions #273: PASS — 132 testy Python, testy Workera, składnia i health wdrożonego Workera.
- YouTube uploader: zmieniono upload na strumieniowy transfer blokami 8 MiB z obsługą odpowiedzi 308 i wznowieniem od bajtu wskazanego w nagłówku `Range`; dodano walidację zakresu, test wieloczęściowego uploadu oraz test hosta docelowego. GitHub Actions #268: PASS — 131 testów Python, testy Workera, składnia modułu i kontrole wdrożonego endpointu.
- Backup: weryfikator sprawdza teraz SHA-256 zaszyfrowanego artefaktu przed próbą odszyfrowania, a następnie hash plaintextu i integralność SQLite. GitHub Actions #264: PASS — test wykrywa uszkodzony artefakt przed wywołaniem age.
- Audyt bezpieczeństwa uploadów: odpowiedzi API dostarczały URL-e transferowe, do których klient wysyłał pliki; dodano ścisłe allowlisty hostów TikTok `open-upload.tiktokapis.com` i YouTube `www.googleapis.com`, blokadę innych hostów, portów, userinfo i fragmentów. Dodano testy negatywne dla niezaufanych URL-i. Oficjalne dokumentacje potwierdzają hosty uploadowe: TikTok Upload/Direct Post oraz Google resumable upload.
- GitHub Actions #260: PASS — 129 testów Python, testy Workera, składnia modułu oraz health i read-only endpoint wdrożonego Workera. Commity bezpieczeństwa #257–#258 miały czerwone przebiegi pośrednie przed aktualizacją fixture testowych; końcowy commit #260 przeszedł pełny workflow.
- Audyt rzeczywistego kanału vidIQ potwierdził `Memory Agent` i handle `@memoryagent-r3c` (provider zwraca handle małymi literami; zachowujemy zapis użytkownika `@MemoryAgent-r3c` w dokumentacji projektu).
- Naprawiono regresyjny test profili: oczekiwany handle YouTube zmieniono z `@MemoryAgent-r3` na `@MemoryAgent-r3c`; commit `88f05cea4cec0932f54f9fa6941652d613a782fc`. Odczyt pliku po zapisie potwierdził zmianę; CI workflow #115 jest QUEUED, więc wynik testu pozostaje niepotwierdzony.

## Najważniejsze blokady

- Publora Starter: 15 publikacji miesięcznie, 2 wykorzystane, 13 pozostało; 3 aktywne sloty harmonogramu, 7-dniowy horyzont.
- Metricool: limity planu nie zostały potwierdzone; nie zakładać wartości.
- Worker nie ma poświadczeń providerów; połączenia w ChatGPT nie są automatycznie dostępne w Cloudflare.

1. Publora pipeline ma testy PASS, ale limit 15/mies. jest za mały dla docelowego wolumenu. Natywne TikTok/YouTube adaptery są gotowe na poziomie kodu; produkcyjne uruchomienie wymaga OAuth, oficjalnych audytów i scheduler/media artifact handoff.
2. Brak backendowych poświadczeń Publora/Metricool w bezpiecznych sekretach; połączenia ChatGPT nie są dostępne bezpośrednio dla Workera/GitHub Actions.
3. vidIQ potwierdził kanał `Memory Agent`, handle `@memoryagent-r3c`, ID `UCOE1EX9WZGDesaJNYIEhj7g`; Metricool wskazuje inne ID `UCRmmEQysOmUbs8mpZEOgtLw`, więc mapowanie YouTube jest BLOCKED i publikacja przez Metricool zabroniona do czasu naprawy.
4. Renderer FFmpeg jest dostępny i ma smoke/regression tests; nie ma jeszcze potwierdzonego, end-to-end handoff artefaktu do natywnych publisherów w środowisku produkcyjnym.
5. Renderer działa w testach; pełne automatyczne generowanie treści i łączenie research → scenariusz → render → publikacja nadal nieukończone.
6. Brak bezpiecznego, odseparowanego miejsca backupu i testu restore.
7. Nie wykonano jeszcze pierwszego zaplanowanego przebiegu Cron.
8. Nie wykonano żadnej publikacji publicznej.

## Zasada wznowienia

Zawsze najpierw odczytaj ten plik, deployment log, audyt bazowy i execution plan. Nie odtwarzaj starych flow z pamięci ani nie zmieniaj działających elementów bez testów.
