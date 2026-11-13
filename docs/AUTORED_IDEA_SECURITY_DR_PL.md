# AUTORED IDEA — bezpieczeństwo, monitoring i Disaster Recovery

**Wersja:** 0.1  
**Data:** 2026-11-13  
**Status:** plan kontroli; wdrożenie i testy DR nieukończone

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
- [ ] Backup danych operacyjnych szyfrowany i oddzielony od produkcji.
- [ ] Integralność backupu automatycznie sprawdzana.
- [ ] Odtworzenie przetestowane i udokumentowane.
- [ ] RPO/RTO zmierzone, nie tylko zadeklarowane.
- [ ] Sekrety nie pojawiają się w logach ani artefaktach CI.
- [ ] Procedura rotacji tokenów przećwiczona.
- [ ] Po awarii system wznawia zadania bez duplikatów.

## 7. Otwarte blokady

- Brak potwierdzonej infrastruktury produkcyjnej i magazynu kopii.
- Brak aktywnych połączeń w projekcie Activepieces.
- Brak testu odtworzenia, bo nie istnieje zatwierdzona kopia produkcyjnej bazy.
- Nie wdrażać Cloudflare R2 ani płatnego magazynu w ramach obecnego budżetu.
