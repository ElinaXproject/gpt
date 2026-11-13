# AUTORED IDEA — bezpieczeństwo, monitoring i Disaster Recovery

**Wersja:** 0.2  
**Data:** 2026-11-13  
**Status:** D1 Time Travel VERIFIED w środowisku testowym; kopia off-site i długoterminowa nadal BLOCKED

## 1. Model zagrożeń

| Zagrożenie | Skutek | Kontrola zapobiegawcza | Dowód testu |
|---|---|---|---|
| Utrata tokenu / wygaśnięcie OAuth | brak publikacji | kontrola ważności, alert, minimalne scope | symulacja 401/refresh |
| Wyciek tokenu lub klucza | przejęcie konta | secret manager, brak sekretów w logach/Repo | skan sekretów |
| Duplikat po timeout | podwójny post | idempotency key, reconciliation przed retry | test timeout po stronie platformy |
| Zły plik lub kodek | odrzucona publikacja | FFprobe, walidacja rozmiaru, proporcji, czasu | zestaw plików poprawnych/błędnych |
| Błędny profil docelowy | publikacja na złym koncie | allowlist account_id, kontrola przed wysyłką | test cross-account |
| Brak limitu / limit planu | kolejka nie działa | quota ledger, circuit breaker, fallback | symulacja limitu |
| Utrata bazy lub mediów | brak możliwości wznowienia | kopie i odtwarzanie; hash i retencja | test restore |
| Awaria workera | przerwany proces | kolejka, heartbeat, retry ograniczone | kill worker / resume |
| Naruszenie praw autorskich | usunięcie treści / roszczenie | rejestr licencji i źródeł, blokada publikacji | test brakującej licencji |
| Błędna treść faktograficzna | dezinformacja | źródła, fact-check, human gate dla ryzykownych treści | test fałszywego twierdzenia |
| Niebezpieczna lub nieodpowiednia treść | naruszenie zasad i szkoda odbiorcy | safety review; blokada do pozytywnej oceny | test treści blokowanej |
| Zmiana API platformy | przerwa publikacji | kontraktowe testy adapterów, monitoring błędów | test fixture / sandbox |
| Nadmierna retencja | ekspozycja danych | minimalizacja, retencja i usuwanie | test usuwania danych |

## 2. Sekrety i uprawnienia

- Tokeny OAuth i API przechowuje wyłącznie zaszyfrowany magazyn sekretów platformy.
- Nigdy nie commitować plików `.env`, tokenów, cookies, refresh tokenów, kluczy prywatnych ani danych osobowych.
- Rozdzielić środowiska DEV / TEST / PROD i poświadczenia.
- Minimalne uprawnienia: TikTok tylko wymagane scope; YouTube tylko `youtube.upload` do uploadu.
- Rotować poświadczenia po podejrzeniu wycieku; natychmiast unieważnić utracony token.
- Logi maskują Authorization, cookies, query tokeny i prywatne URL-e.
- Konta platformy i repozytorium zabezpieczyć MFA, jeśli dostępne.

## 3. Backup & Disaster Recovery — obowiązkowy moduł

Zakres kopii:
- kod, konfiguracja, definicje przepływów i schematy;
- dokumentacja, decyzje, testy i historia zmian;
- metadane kalendarza i publikacji, o ile retencja na to pozwala;
- ustawienia i mapowanie profili;
- rejestr licencji, hashy i statusów mediów.

Sekrety nie są kopiowane w postaci jawnej. Backup zawierający dane wrażliwe musi być szyfrowany i przechowywany oddzielnie od produkcji.

Zasady:
1. Git jako wersjonowane źródło kodu i dokumentacji.
2. Automatyczna kopia danych operacyjnych co najmniej raz dziennie po uruchomieniu bazy produkcyjnej.
3. Kopia przed każdą migracją, zmianą schematu i wdrożeniem.
4. Retencja: 7 kopii dziennych, 4 tygodniowe, 3 miesięczne — do zatwierdzenia w implementacji i w granicach darmowej przestrzeni.
5. Weryfikacja integralności SHA-256.
6. Co miesiąc test odtworzenia do środowiska testowego; po każdej zmianie backupu — test próbki.
7. RPO docelowe: 24 godziny dla metadanych; RTO docelowe: 4 godziny, o ile dostępna infrastruktura pozwoli.
8. Nie uruchamiać dodatkowego płatnego storage. Jeśli brak bezpłatnego, bezpiecznego miejsca, oznaczyć backup jako BLOCKED zamiast udawać, że istnieje.

### 3A. Potwierdzony mechanizm D1 Time Travel

- Produkcyjna baza `autored_idea_db` działa na storage backend `production`, region EEUR, jurysdykcja EU.
- D1 Time Travel jest automatycznie włączony; nie wymaga ręcznego uruchamiania backupu.
- Aktualny bookmark oraz bookmark historyczny zostały pobrane przez Cloudflare API.
- Test odtworzenia wykonano wyłącznie na tymczasowej bazie `autored_idea_dr_test`: zapisano rekord bazowy, pobrano bookmark, dodano drugi rekord, przywrócono bookmark i potwierdzono, że został tylko rekord bazowy.
- Testowa baza została po teście usunięta. Baza produkcyjna nie była przywracana ani modyfikowana w ramach testu.
- Konserwatywne założenie dla darmowego planu: 7 dni Time Travel; dokumentacja Cloudflare podaje 30 dni dla planu płatnego. Nie zakładać 30 dni bez potwierdzenia planu.
- Time Travel nie zastępuje niezależnej kopii off-site ani backupu mediów i dokumentacji.

Źródła: https://developers.cloudflare.com/d1/reference/time-travel/ ; https://developers.cloudflare.com/d1/platform/limits/

### 3B. R2 — stan aktywacji
- Próba odczytu listy bucketów zwróciła Cloudflare API 403 / code 10042: `Please enable R2 through the Cloudflare Dashboard`.
- R2 nie został aktywowany ani nie utworzono bucketu; nie uruchomiono płatnej usługi.
- Oficjalny cennik wskazuje bezpłatny Standard Tier: 10 GB-month, 1 mln operacji Class A i 10 mln Class B miesięcznie, bez opłat za egress. Strona produktu Cloudflare deklaruje możliwość rozpoczęcia bez karty; mimo tego w tym koncie R2 wymaga ręcznego włączenia w Dashboard.
- Do czasu ręcznego włączenia R2 i sprawdzenia limitów nie oznaczać kopii off-site jako gotowej.

Źródło: https://developers.cloudflare.com/r2/pricing/

### 3C. Codzienna kopia off-site — workflow gotowy, aktywacja wymaga sekretów

Workflow `.github/workflows/d1-backup.yml`:
- uruchamia się raz dziennie o 10:00 Europe/Warsaw (dwa wywołania UTC z bramką DST);
- eksportuje D1 przez przypięty Wrangler `4.161.0`;
- szyfruje SQL przez age przed wysłaniem artefaktu;
- tworzy manifest SHA-256 dla pliku jawnego i zaszyfrowanego;
- przechowuje zaszyfrowany artefakt do 90 dni;
- narzędzie `scripts/verify_d1_backup.py` odszyfrowuje lokalnie, porównuje SHA-256, wykonuje SQLite `PRAGMA integrity_check` i sprawdza obecność 6 tabel; testy offline PASS.
- przy braku sekretów pomija harmonogram z ostrzeżeniem; ręczne uruchomienie zgłasza brak konfiguracji.

Wymagane ręczne ustawienia właściciela:
1. Utworzyć lokalnie parę age: `age-keygen -o autored-backup-key.txt`.
2. Zachować plik prywatny offline; nigdy nie commitować go ani nie przesyłać do rozmowy.
3. Dodać publiczny recipient `age1...` jako GitHub repository variable `BACKUP_AGE_RECIPIENT`.
4. Utworzyć Cloudflare API Token z minimalnym uprawnieniem D1 do eksportu bazy `autored_idea_db` i zapisać jako GitHub Actions secret `CLOUDFLARE_API_TOKEN`.
5. Po dodaniu ustawień uruchomić workflow ręcznie i sprawdzić, czy powstał zaszyfrowany artefakt.

Uwaga: eksport D1 może czasowo blokować zapytania do bazy. Baza ma obecnie ok. 96 KB, ale workflow nie powinien być uruchamiany równocześnie z migracją ani testem restore. Pełny test odszyfrowania i odtworzenia artefaktu pozostaje do wykonania po dodaniu klucza prywatnego i sekretu API.

## 4. Monitoring i automatyczna naprawa

Monitorować:
- heartbeat scheduler/workera;
- czas wykonania i status każdego etapu;
- odsetek błędów publikacji per platforma i profil;
- wygasanie OAuth i błędy uprawnień;
- zużycie miesięcznych limitów i liczbę elementów w kolejce;
- rozmiar bazy, retencję i powodzenie backupu;
- błędy jakości mediów i kompletność metadanych.

Automatyczne naprawy dozwolone:
- retry tylko dla błędów przejściowych (429/5xx/network timeout), z exponential backoff i jitter;
- odświeżenie OAuth przez oficjalny mechanizm;
- odłożenie zadania do dead-letter queue po przekroczeniu limitu prób;
- ponowna walidacja pliku po zmianie renderu;
- alert i przejście w tryb bezpieczny przy błędzie autoryzacji, limitu lub niepewności publikacji.

Automatyczne naprawy zabronione:
- ślepe ponawianie publikacji po timeout bez sprawdzenia, czy post już istnieje;
- zmiana profilu docelowego w celu obejścia limitu;
- tworzenie nowych kont/projektów API w celu obejścia limitów;
- wyłączanie walidacji praw, AI disclosure lub kontroli jakości;
- zmiana prywatności lub widoczności treści bez jawnej konfiguracji.

## 5. Procedury incydentów

### P1 — możliwy wyciek poświadczeń
1. Zatrzymać publikację.
2. Unieważnić poświadczenie w panelu dostawcy.
3. Wygenerować nowe poświadczenie i zapisać w secret managerze.
4. Przejrzeć logi bez ujawniania sekretu.
5. Wykonać test autoryzacji i publikacji w trybie prywatnym/testowym.
6. Wznowić dopiero po VERIFIED.

### P2 — błąd publikacji
1. Odczytać status zadania i platformy.
2. Sprawdzić platform_post_id przed retry.
3. Rozpoznać błąd terminalny vs przejściowy.
4. Zastosować retry wyłącznie dla błędu przejściowego.
5. Dla błędu terminalnego przenieść do dead-letter i zachować diagnostykę.

### P3 — utrata danych
1. Wstrzymać zapisy.
2. Wybrać najnowszą kopię z potwierdzoną integralnością.
3. Odtworzyć w środowisku odizolowanym.
4. Porównać liczbę rekordów, hashe i referencje.
5. Przełączyć dopiero po teście akceptacyjnym.

## 6. Kryteria gotowości DR

- [ ] Backup kodu i dokumentacji potwierdzony.
- [x] Automatyczny point-in-time recovery D1 potwierdzony testem restore w izolowanej bazie.
- [ ] Backup danych operacyjnych szyfrowany i oddzielony od produkcji (off-site).
- [ ] Integralność backupu automatycznie sprawdzana.
- [ ] Odtworzenie przetestowane i udokumentowane.
- [ ] RPO/RTO zmierzone, nie tylko zadeklarowane.
- [ ] Sekrety nie pojawiają się w logach ani artefaktach CI.
- [ ] Procedura rotacji tokenów przećwiczona.
- [ ] Po awarii system wznawia zadania bez duplikatów.

## 7. Otwarte blokady

- D1 Time Travel jest aktywny i przetestowany; workflow szyfrowanej kopii off-site jest przygotowany, ale oczekuje na API token i publiczny recipient age. R2 pozostaje wyłączony.
- Brak aktywnych połączeń w projekcie Activepieces.
- Brak testu odtworzenia pełnej kopii produkcyjnej do oddzielnego środowiska; test Time Travel wykonano na tymczasowej bazie testowej.
- Nie wdrażać Cloudflare R2 ani płatnego magazynu w ramach obecnego budżetu.
