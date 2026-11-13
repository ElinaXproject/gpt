# Audyt wtyczek, integracji i architektury produkcji treści

**Data bazowa:** 2026-11-13  
**Status:** AUDYT W TOKU — tylko odczyt i testy; bez zmian w działających workflow  
**Repozytorium:** `ElinaXproject/gpt`

## 1. Zasady nadrzędne

1. Priorytet: darmowe rozwiązania bez karty, abonamentu, ukrytych kosztów i płatnych API. Nie obchodzimy limitów.
2. Jakość materiału jest ważniejsza od liczby funkcji. Większy limit może przeważyć tylko wtedy, gdy różnica jakości jest mała, a korzyść operacyjna duża.
3. Nie zastępować działającego komponentu bez testu porównawczego, planu cofnięcia i potwierdzonej przewagi.
4. Każdy komponent ma mieć jedną jasno określoną rolę. Unikać dwóch systemów wykonujących ten sam etap bez uzasadnienia.
5. Nie oznaczać materiału jako gotowego ani opublikowanego bez sprawdzenia wyniku w systemie docelowym.
6. Zmiany małe, odwracalne i wersjonowane. Najpierw kopia/branch, potem test, wdrożenie i regresja.
7. Każdy etap kończy się aktualizacją tego dokumentu, rejestrem decyzji i dowodem testu.
8. Nie zapisywać tokenów, haseł, danych płatniczych ani prywatnych danych w repozytorium lub logach.
9. W przypadku limitów nieznanych lub niepotwierdzonych status to UNKNOWN — nie zakładamy darmowego użycia.
10. Nie dodawać nowego narzędzia tylko dlatego, że istnieje. Musi rozwiązywać konkretny problem lepiej od obecnego zestawu.

## 2. Rejestr dostępnych grup narzędzi

Lista obejmuje wszystkie grupy narzędzi widoczne w bieżącym środowisku. Dostępność funkcji nie oznacza automatycznie, że konto zewnętrzne jest połączone lub że funkcja jest bezpłatna.

| Grupa | Zakres funkcji | Najlepsza rola w systemie | Stan połączenia / uwagi |
|---|---|---|---|
| Activepieces | Automatyzacje, harmonogramy, AI, tabele, testy, kroki i integracje | Główny silnik automatyzacji | Projekt Memory's Project; 1 aktywny flow. |
| Automations | Zadania cykliczne i monitorujące | Harmonogram zadań ChatGPT | 4 zapisane automatyzacje; 2 aktywne, 2 wyłączone. |
| vidIQ | Trendy YouTube, słowa kluczowe, konkurencja, statystyki, tytuły, miniatury, skrypty, głos, klipy i narzędzia wideo | Analityka YouTube i optymalizacja treści | YouTube Memory Agent połączony; 130/150 kredytów Free. |
| Metricool | Planowanie, publikacja, analityka, najlepsze godziny, marki | Analityka i kalendarz społecznościowy | Marka RED ABSURD IDEA widoczna; szczegóły kanałów wymagają osobnego testu. |
| Publora | Publikacja, harmonogram, media, kolejka, statystyki, webhooki, audyt | Główny adapter publikacji social | Starter: 15 postów/mies., 3 konta, limit 7 dni; TikTok @pieknemedia aktywny. |
| ElevenLabs | TTS, transkrypcja, głosy, muzyka, obrazy, wideo, agenci, workflow kreatywne | Lektor, audio i testy generowania mediów | Narzędzia dostępne; saldo i limity konta do osobnego sprawdzenia przed generacją. |
| GitHub | Repozytoria, pliki, PR, issues, Actions, CI, workflow | Główne wersjonowane źródło prawdy | Połączony; dostęp do ElinaXproject/gpt. |
| GitLab | Repozytoria, pipeline, issues, MR, skany i CI | Alternatywne repo/CI | Połączony; nie dublować GitHub bez powodu. |
| Notion | Dokumenty, bazy, zadania, wiki, komentarze, kalendarz | Operacyjny indeks i baza wiedzy | Połączony; część funkcji MCP wymaga planu Business/Enterprise. |
| Dropbox | Pliki, foldery, historia, Paper, udostępnianie | Archiwum wtórne i transfer plików | Połączony; nie potwierdzono pełnej synchronizacji/backupów. |
| Gmail | Wyszukiwanie, odczyt, etykiety, szkice, wysyłka | Powiadomienia i obsługa korespondencji | Profil nie zwrócił danych; status wymaga diagnozy. |
| Lemma Telepath | Telegram, kanały, wiadomości, pliki, posty, przypomnienia | Komunikacja i powiadomienia | Konfiguracja Telegram nieukończona; nie ponawiać prób przed ukończeniem setupu. |
| Cloudflare | Dokumentacja, API, DNS i usługi platformowe | DNS, edge, Workers i ewentualny hosting | Konto rozpoznane; zasoby i limity do sprawdzenia przed wdrożeniem. |
| Render | Deploy, usługi, bazy, logi, metryki, workflow | Hosting testowy / aplikacyjny | Brak wybranego workspace; darmowe usługi mają ograniczenia i nie są domyślnym produkcyjnym hostingiem. |
| Base44 | Tworzenie i edycja aplikacji, encje, konektory | Szybkie prototypy aplikacji | Brak aplikacji na koncie w chwili kontroli. |
| SentinelX | Serwery, pliki, procesy, usługi, diagnostyka, integracje | Zdalna administracja i diagnostyka | Brak zapisanych integracji; hosty wymagają osobnej kontroli. |
| Remote Desktop Commander | Urządzenia, terminal, pliki, procesy, sesje | Operacje na komputerze użytkownika | Narzędzia dostępne; urządzenia/sesje do weryfikacji przed użyciem. |
| Code Tytor Python | Pisanie, debugowanie, refaktoryzacja i uruchamianie Python | Pomocnicze programowanie | Dostępne narzędzia; limity konta niepotwierdzone. |
| DocVision AI | OCR, PDF, ekstrakcja, walidacja, porównanie i audyt dokumentów | Kontrola dokumentów i OCR | Dostępne narzędzia; limity konta niepotwierdzone. |
| Engram | Długoterminowa pamięć i wyszukiwanie rozmów | Opcjonalna pamięć projektowa | Dostępne narzędzia; nie dublować bez testu przewagi nad GitHub/Notion. |
| OpenAI Platform | Konfiguracja klucza API | Integracje API wymagające klucza | Nie generować klucza ani nie uruchamiać płatnego API w ramach tego audytu. |
| Plugin Management | Wyszukiwanie, instalacja, zależności i uprawnienia wtyczek | Zarządzanie ekosystemem | Dostępne narzędzia; instalacja wymaga jawnej akcji użytkownika. |
| Files / Library | Wyszukiwanie, odczyt, materializacja, archiwum i obrazy referencyjne | Archiwum robocze i zasoby | Dostępne. |
| User Settings | Odczyt i zmiana ustawień ChatGPT | Konfiguracja środowiska | Dostępne. |
| Skills | Instrukcje i procedury dla narzędzi | Standaryzacja pracy | Dostępne katalogi umiejętności; wybierać tylko właściwe dla zadania. |

### Narzędzia natywne

- Web research: wyszukiwanie bieżących informacji i źródeł.
- ImageGen: generowanie i edycja obrazów w rozmowie.
- Python / container: lokalna analiza, testy, przetwarzanie plików i prototypy.
- Personal Context: wyszukiwanie wcześniejszych ustaleń i kontekstu.
- DIL/UI: tworzenie użytecznych widoków, tabel i prostych interfejsów.

## 3. Potwierdzone limity i koszty — stan na dzień audytu

Weryfikacja na oficjalnych stronach producentów; limity mogą się zmienić.

| Usługa | Darmowy zakres / ograniczenie | Wniosek |
|---|---|---|
| Activepieces | Free: 100 kredytów dziennie, nieograniczone flow, bez karty; kroki AI mogą generować dodatkowe koszty modelu. | Dobry kandydat na centralny silnik automatyzacji; kontrolować zużycie AI. |
| vidIQ | Free: 150 AI credits/mies.; research zwykle 5 kredytów, short-form analysis 10, długie video watch 25, thumbnail 22, voiceover 28/1000 znaków, muzyka 25. | Używać selektywnie do YouTube; nie uruchamiać kosztownych generacji bez sprawdzenia kredytów. |
| Publora | Starter: 3 konta, 15 postów/mies., 50 MB video, API/MCP, bez karty. | Dobry darmowy adapter publikacji przy małym wolumenie. |
| Metricool | Free: 1 marka, 20 postów/mies., 30 dni analityki, 5 konkurentów; AI assistant 5 kredytów/markę/mies. | Kandydat do analityki i planowania; nie dublować publikacji bez potrzeby. |
| ElevenLabs | Free: 10 000 kredytów/mies.; brak komercyjnej licencji w darmowym planie. | Testy lektora i audio; przed użyciem komercyjnym sprawdzić licencję i warunki. |
| GitHub | Free: repozytoria publiczne i prywatne, 2 000 minut Actions/mies. dla standardowego konta; dodatkowe usługi mogą być płatne. | Najlepsze miejsce na wersjonowanie, dokumentację i testy. |
| Notion | Free dla pojedynczego użytkownika; pliki do 5 MB, historia 7 dni; część funkcji AI to ograniczona próba. | Używać do indeksu i operacyjnego widoku, nie opierać systemu na płatnym AI Notion. |
| Dropbox Basic | 2 GB przestrzeni. | Tylko kopia/transfer małych plików; nie jedyny backup. |
| Cloudflare Workers Free | 100 000 żądań/dzień, 5 Cron Triggers/konto, limit CPU 10 ms/wywołanie. | Przydatne dla lekkich endpointów i cronów, nie dla ciężkiego renderingu. |
| Render Free | Usługi usypiają po 15 min bez ruchu; 750 h/mies.; darmowy Postgres wygasa po 30 dniach i nie ma backupów. | Nie używać jako krytycznego hostingu ani jedynego magazynu danych. |

Źródła oficjalne:
- Activepieces: https://www.activepieces.com/pricing
- vidIQ: https://vidiq.com/plans/ oraz https://support.vidiq.com/en/articles/15082430-vidiq-mcp
- Publora: https://publora.com/pricing
- Metricool: https://metricool.com/pricing/
- ElevenLabs: https://elevenlabs.io/pricing
- GitHub: https://github.com/pricing
- Notion: https://www.notion.com/pricing
- Dropbox: https://help.dropbox.com/plans/dropbox-basic-faq
- Cloudflare: https://developers.cloudflare.com/workers/platform/limits/
- Render: https://render.com/docs/free

## 4. Pierwsze ustalenia z audytu działających automatyzacji

### Activepieces — generator TikTok

Flow: `FROZONE – generator dwóch szkiców TikTok (codziennie 09:00; bez publikacji)`

- 12 kroków, wszystkie mają status configured.
- Codzienny trigger 09:00 Europe/Warsaw.
- Pobiera historię do 500 rekordów.
- Generuje dokładnie dwa posty: @pieknemedia i @ocenionona6.
- Generuje dwa obrazy, konwertuje do JPEG, sprawdza metadane i zapisuje dwa rekordy do kalendarza.
- Dzisiejszy run produkcyjny: SUCCEEDED, 52,9 s.
- Dwa wcześniejsze testy zakończyły się błędem: parsowanie JSON i generowanie drugiego obrazu.
- Krok AI ma webSearch=false, więc nie wykonuje researchu aktualnych wiadomości.
- Krok AI ma retryOnFailure=false. To ryzyko niezawodności.
- Projekt Activepieces zwrócił zero zapisanych połączeń zewnętrznych; model i generowanie obrazu używają provider='activepieces'. Nie zakładać, że inne integracje są skonfigurowane.
- Flow nie publikuje — zapisuje szkice do kalendarza. Nie zmieniać tego bez osobnej decyzji.

### Publora

- Starter, publikowanie i API/MCP aktywne.
- 1 połączone konto TikTok @pieknemedia.
- 15 postów/miesiąc; 2 wykorzystane, 13 pozostało.
- 3 miejsca na aktywne zaplanowane posty; aktualnie 0 zajętych.
- Horyzont planowania 7 dni.
- Analityka nie jest dostępna w tym planie.

### vidIQ

- Połączony kanał YouTube Memory Agent, canPublish=true.
- 130/150 kredytów miesięcznych.
- Free research i funkcje 0-kredytowe należy odróżniać od wywołań zużywających kredyty.
- Oficjalny opis MCP informuje, że MCP nie przesyła nowego filmu bezpośrednio na YouTube; publikację nowego filmu trzeba wykonać w YouTube Studio lub innym potwierdzonym narzędziu uploadu.
- Nie przypisywać vidIQ roli kreatora ani publikatora w workflow, dopóki nie ma potwierdzonego wywołania i testu.

### Inne

- Metricool: jedna marka jest widoczna; sprawdzić osobno, które kanały są aktywne i czy analityka działa.
- Notion: podstawowe strony i operacje są dostępne; część wyszukiwania baz i funkcji komentarzy wymaga wyższego planu.
- Telepath: setup Telegram nieukończony.
- Render: brak wybranego workspace; nie wybierać samodzielnie.
- Base44: brak aplikacji na koncie w chwili sprawdzenia.
- Gmail: odczyt profilu zwrócił pusty wynik; wymaga diagnozy.
- SentinelX: lista integracji jest pusta.

## 5. Wstępna architektura docelowa — do potwierdzenia testami

### TikTok / profile społecznościowe

1. Research i plan tematów: web + źródła pierwotne; Metricool/vidIQ tylko jako dodatkowe sygnały trendów.
2. Redakcja: model AI w Activepieces, ale dopiero po weryfikacji faktów i zgodności z profilem.
3. Kreacja: test porównawczy obecnego generatora Gemini z dostępnymi narzędziami ElevenLabs/ImageGen; ocena realizmu, zgodności z promptem, jakości kompozycji i powtarzalności.
4. Walidacja: JSON schema, antyduplikaty, prawa do materiałów, format, rozdzielczość, czytelność i prompt audit.
5. Kalendarz: jedna baza jako źródło prawdy; nie duplikować postów w kilku plannerach.
6. Publikacja: Publora jako podstawowy adapter, o ile potwierdzone limity i kanały wystarczą; Metricool tylko jeśli testy wykażą przewagę w analityce lub publikacji.
7. Po publikacji: sprawdzenie statusu i identyfikatora posta w platformie docelowej.

### YouTube Memory Agent

1. Research technologiczny 24–72 h ze źródeł pierwotnych i renomowanych mediów.
2. vidIQ: trendy, słowa kluczowe, outliers, konkurencja, ocena tytułów i miniatur — selektywnie, kontrolując kredyty.
3. Redakcja: scenariusz, źródła, daty, weryfikacja faktów i rozdzielenie informacji od spekulacji.
4. Produkcja: osobne testy lektora, grafiki, montażu i miniatur.
5. Upload: tylko potwierdzone narzędzie z odpowiednimi uprawnieniami.
6. Weryfikacja: odczyt filmu w YouTube po publikacji, status, tytuł, miniatura, widoczność i link.

### Jakość promptów i materiałów

Każdy prompt wizualny ma mieć:
- cel, odbiorcę i format;
- blokadę cech, które muszą pozostać niezmienne;
- kompozycję, perspektywę, oświetlenie, styl i poziom realizmu;
- negatywne wymagania (np. brak tekstu, watermarków, artefaktów);
- kryteria akceptacji;
- kontrolę zgodności wyniku z poleceniem.

Każdy prompt tekstowy ma mieć:
- rolę i zadanie;
- źródła i zakres aktualności;
- format wyjścia;
- ograniczenia faktograficzne;
- zasady unikania powtórzeń;
- kryteria jakości i obsługę niepewności.

### Backup & Disaster Recovery — obowiązkowy moduł

- Regularne kopie kodu, danych, konfiguracji, dokumentacji, automatyzacji, promptów i materiałów.
- Kopie oddzielone od środowiska produkcyjnego.
- Szyfrowanie kopii zawierających dane wrażliwe.
- Wersjonowanie, retencja i kontrola integralności.
- Automatyczne raportowanie nieudanych kopii.
- Okresowe próby odtworzenia; sama obecność pliku backupu nie oznacza, że można go odtworzyć.
- GitHub nie może być jedyną kopią wszystkich danych; Dropbox Basic 2 GB nie jest wystarczającym jedynym backupem.

## 6. Plan prac — kolejność i status

Statusy: `TODO`, `DOING`, `BLOCKED`, `DONE`, `VERIFIED`. Zadanie przechodzi do VERIFIED dopiero po niezależnym sprawdzeniu wyniku.

| ID | Priorytet | Zadanie | Kryterium ukończenia | Status |
|---|---|---|---|---|
| A01 | P0 | Pełny spis narzędzi i ich ról | Wszystkie 25 grup ujęte w rejestrze | DONE |
| A02 | P0 | Zbadać darmowe plany i limity | Oficjalne źródła, koszt i limity zapisane | DOING |
| A03 | P0 | Potwierdzić połączenia i stan kont | Status każdej usługi: connected / partial / blocked / unknown | DOING |
| A04 | P0 | Zmapować obecne workflow i zależności | Każdy flow, trigger, kroki, konto docelowe i wynik | DOING |
| A05 | P0 | Zbudować macierz jakości kreatorów | Ten sam brief i ocena tekstu/obrazu/wideo/głosu | TODO |
| A06 | P0 | Ustalić architekturę bez dublowania | Jedno narzędzie główne na etap, adaptery awaryjne | TODO |
| A07 | P1 | Dodać research i fact-check do treści aktualnych | Źródła, daty, cytowalne dowody, brak zgadywania | TODO |
| A08 | P1 | Dodać prompt audit i walidację obrazów | Checklista i test porównawczy generacji | TODO |
| A09 | P1 | Wzmocnić obsługę błędów Activepieces | Retry tylko dla błędów przejściowych, timeout, alert, idempotencja | TODO |
| A10 | P1 | Weryfikacja publikacji i monitoring | Potwierdzony post ID, status, URL i kontrola błędu | TODO |
| A11 | P1 | Backup & Disaster Recovery | Backup, szyfrowanie, retencja, integralność, restore test | TODO |
| A12 | P1 | Uporządkować dokumentację i rejestr decyzji | Jeden indeks, wersjonowanie, brak sprzecznych instrukcji | TODO |
| A13 | P2 | Audyty cykliczne | Cotygodniowy audyt błędów, limitów, jakości i zmian API | TODO |
| A14 | P2 | Optymalizacja kosztów i limitów | Wykorzystanie darmowych limitów bez ryzyka przerwania pracy | TODO |

## 7. Metoda porównywania narzędzi

Ocena 0–5; wynik ważony:
- Jakość rezultatu: 40%
- Niezawodność i powtarzalność: 25%
- Funkcjonalność dopasowana do zadania: 15%
- Darmowe limity i brak karty: 15%
- Łatwość integracji: 5%

Wyjątek: jeśli narzędzie ma istotnie większą funkcjonalność lub limit, można je wybrać mimo nieco niższej jakości — decyzja musi mieć zapisane uzasadnienie. Narzędzia oceniać na tych samych wejściach i według tych samych kryteriów. Wyników nie porównywać na podstawie reklam producenta.

## 8. Zasady niezawodności

- Retry tylko dla błędów przejściowych; nie ponawiać automatycznie błędów walidacji lub autoryzacji.
- Każdy etap produkcji ma walidację wejścia i wyjścia.
- Każdy zapis lub publikacja ma klucz idempotencji albo kontrolę duplikatu.
- Po timeout sprawdzić stan docelowy przed ponowieniem.
- Nie uznawać statusu SUCCEEDED za dowód jakości treści; osobno kontrolować jakość.
- Błędy i wyniki przechowywać z identyfikatorem runu, krokiem, czasem i działaniem naprawczym.
- Zmiany w działającym flow robić przez kopię/wersję testową, a następnie regresję.
- W razie pogorszenia wyniku przywrócić ostatnią wersję VERIFIED.

## 9. Rejestr decyzji

| Data | Decyzja | Uzasadnienie | Status |
|---|---|---|---|
| 2026-11-13 | Nie zastępować obecnego generatora TikTok przed benchmarkiem | Obecny flow ma udane runy produkcyjne; brakuje porównania jakości | ACTIVE |
| 2026-11-13 | Użyć vidIQ do analityki YouTube, nie zakładać automatycznej produkcji/publikacji | Limity Free i koszt kredytów; MCP ma ograniczenia uploadu | ACTIVE |
| 2026-11-13 | Publora pozostaje podstawowym kandydatem do publikacji social | Aktywny kanał TikTok i potwierdzony darmowy limit | ACTIVE |
| 2026-11-13 | GitHub pozostaje wersjonowanym źródłem prawdy dla dokumentacji technicznej | Repo i odczyt/zapis potwierdzone | ACTIVE |

## 10. Następny krok

Dokończyć A02–A04: sprawdzić pozostałe plany, połączenia i workflow; potem przygotować benchmark kreatorów. Do tego czasu nie zmieniać działającego generatora, harmonogramów ani publikatorów.


## 11. Automatyzacje cykliczne — kontrola 2026-11-13

| Zadanie | Stan | Najbliższy termin | Wniosek |
|---|---|---|---|
| Memory Agent – monitoring i produkcja YouTube | ENABLED | 2026-11-14 08:00 Europe/Warsaw | Brak zarejestrowanego wcześniejszego uruchomienia w odczycie; prompt przewiduje research i wykorzystanie vidIQ. |
| Codzienna obsługa TikTok i audyt | ENABLED | 2026-11-13 15:45 Europe/Warsaw | Osobna automatyzacja ChatGPT; porównać z Activepieces, aby uniknąć podwójnego tworzenia materiałów. |
| Cotygodniowy audyt środowiska pracy | DISABLED | 2026-11-19 09:00 Europe/Warsaw | Istniejący audyt tygodniowy jest wyłączony. Nie aktywować bez osobnej zgody. |
| Codzienna kontrola statystyk TikToka | DISABLED | 2026-11-14 10:00 Europe/Warsaw | Do sprawdzenia, czy zadanie nie dubluje Metricool lub innych raportów. |



## 12. Ponowna kontrola połączeń i workflow — 2026-11-13 14:15 UTC

Kontrola wykonana ponownie w trybie read-only. Nie zmieniano żadnego workflow ani publikacji.

### Activepieces
- Poprawny identyfikator projektu: `Z1qa7Ph0wSCS8sIQWfzCM`. Pierwsza próba ustawienia kontekstu po nazwie nie powiodła się; ponowiono z ID i kontekst ustawiono poprawnie.
- Lista flow: dokładnie 1 flow; `FROZONE – generator dwóch szkiców TikTok (codziennie 09:00; bez publikacji)`, ID `xqrXQtgQMAhS2QhGDyYBI`, ENABLED, published.
- Struktura: 12 kroków, wszystkie configured/valid. Kolejność: harmonogram → odczyt historii (limit 500) → AI tworzące 2 posty → parser JSON → obraz profilu pieknemedia → JPEG → metadata → obraz profilu ocenionona6 → JPEG → metadata → rozdzielenie rekordów → zapis do tabeli.
- Harmonogram potwierdzony w strefie Europe/Warsaw, godz. 09:00, również w weekendy.
- Lista połączeń OAuth Activepieces: 0. To nie blokuje obecnego flow, bo generowanie AI/obrazów używa skonfigurowanego provider Activepieces; nie ma natomiast połączeń OAuth do zewnętrznych aplikacji w tym projekcie.
- Wniosek: obecny generator jest aktywny i poprawnie skonfigurowany na poziomie struktury. Nie jest to dowód jakości każdego wygenerowanego materiału ani publikacji — flow tylko zapisuje szkice.

### Publora — odczyt konta i połączeń
- Plan Starter, publishing/API/MCP aktywne, analytics niedostępne.
- Limit miesięczny: 15 postów, wykorzystane 2, pozostało 13; reset 2026-12-01 UTC.
- Kolejka: 3 aktywne zaplanowane posty maksymalnie, obecnie 0; horyzont planowania do 7 dni.
- Limit połączeń: 3, wykorzystane 1, pozostałe 2.
- Jedyny podłączony kanał: TikTok `@pieknemedia`; connectionStatus=active, tokenStatus=valid; ostatni udany post 2026-11-12 11:28:45 UTC; brak ostatniego błędu.
- Ważna luka: `@ocenionona6` NIE jest podłączony do Publora w odczycie z 2026-11-13. Nie wolno zakładać, że oba profile mogą być publikowane przez Publora.

### Metricool
- Widoczna jedna marka: `RED ABSURD IDEA`, strefa Europe/Warsaw.
- W danych marki są: Instagram `violetx3p`, Pinterest `calistoxmass`, TikTok `ocenionona6`, YouTube `UCRmmEQysOmUbs8mpZEOgtLw`.
- To potwierdza obecność tych identyfikatorów w konfiguracji marki, ale nie potwierdza jeszcze testem uprawnień publikacji ani odczytu analityki dla każdego kanału.
- Rozbieżność do rozstrzygnięcia: Metricool pokazuje TikTok `ocenionona6`, podczas gdy Publora ma aktywny tylko `pieknemedia`. Nie dublować publikacji; przed wyborem adaptera sprawdzić uprawnienia i dokładne profile.

### vidIQ
- Saldo sprawdzone bez zużywania kredytów: 130/150 kredytów odnawialnych; 0 kredytów bonusowych; odnowienie 2026-12-10 10:41:03 UTC.

### Cloudflare
- Odczyt `whoami` potwierdza połączenie konta. Zasoby, strefy DNS i Workers nie były jeszcze sprawdzane; status zasobów pozostaje UNKNOWN.

### Statusy etapów po tej kontroli
- A01 — DONE.
- A02 — DOING (potwierdzone wybrane limity; pozostałe usługi nadal wymagają weryfikacji).
- A03 — DOING (potwierdzone Activepieces, Publora, Metricool, vidIQ i tożsamość Cloudflare; pozostałe połączenia nadal do sprawdzenia).
- A04 — DOING (zmapowano cały jedyny flow Activepieces; automatyzacje ChatGPT i pozostałe procesy trzeba jeszcze zestawić z harmonogramami i wykryć duplikacje).
- A05–A14 — TODO.

### Ryzyka wymagające rozwiązania przed zmianami
1. Publora nie ma połączenia `@ocenionona6`; nie wolno planować dla niego publikacji tym adapterem.
2. Activepieces nie ma OAuth connections; integracje zewnętrzne wymagają osobnego połączenia lub jawnego adaptera.
3. Metricool i Publora mają różne zestawy profili; trzeba ustalić, który profil ma być obsługiwany przez które narzędzie, bez publikowania próbnego materiału.
4. Błędy JSON i drugiego obrazu z poprzednich testów pozostają otwarte. Naprawa dopiero na kopii flow i po testach, nie w produkcji.


## 13. Obowiązkowy rejestr zmian i aktualizacja dokumentacji na bieżąco

**Zasada nadrzędna:** dokumentacja jest żywym rejestrem stanu faktycznego, a nie opisem planowanego systemu. Każda zmiana — planowana i nieplanowana — musi zostać odnotowana w tym samym cyklu pracy.

### Zdarzenia wymagające aktualizacji
- zmiana konfiguracji, promptu, harmonogramu, połączenia, uprawnień lub limitu;
- nowy workflow, krok, integracja, konto lub profil;
- błąd, awaria, timeout, nieudany run albo nieoczekiwany wynik;
- naprawa, rollback, wyłączenie, usunięcie lub zastąpienie komponentu;
- publikacja, odrzucenie materiału lub zmiana statusu publikacji;
- zmiana planu darmowego, limitu, ceny, warunków licencji lub dostępności API.

### Procedura obowiązkowa dla każdej zmiany
1. **Przed zmianą:** odczytać aktualny stan i wskazać elementy zależne. Przy ryzyku regresji utworzyć kopię/branch i zachować możliwość rollbacku.
2. **Wykonanie:** zmienić tylko zakres konieczny; nie naruszać działających elementów bez uzasadnienia.
3. **Test:** sprawdzić wynik w systemie źródłowym, wykonać test funkcjonalny i — gdy dotyczy — regresję.
4. **Dokumentacja:** w tym samym zadaniu zaktualizować właściwą sekcję, status Axx, rejestr decyzji i dziennik zmian. Zapisać datę/czas Europe/Warsaw, identyfikator zasobu/runu, wynik testu, ryzyko i rollback.
5. **Weryfikacja:** ponownie odczytać zapisany plik z GitHub. Nie oznaczać zadania jako DONE/VERIFIED, jeśli nie ma dowodu.
6. **Raport:** użytkownik otrzymuje krótki wynik: co faktycznie zmieniono, co przetestowano, co nadal nie działa i link do dowodu.

### Reguły statusu i rzetelności
- Zmiana bez testu = CHANGED / UNVERIFIED, nie DONE.
- Zgłoszony problem bez reprodukcji = OPEN / NEEDS DIAGNOSIS.
- Naprawa bez testu regresyjnego = FIXED / UNVERIFIED.
- Brak odczytu integracji = UNKNOWN, nigdy domyślnie CONNECTED.
- Nieplanowana zmiana nie może pozostać wyłącznie w historii rozmowy.
- Nie wolno deklarować pracy w tle ani automatycznej synchronizacji, jeśli nie działa do tego potwierdzony mechanizm.
- Jeśli aktualizacja GitHub nie powiedzie się, należy jawnie zgłosić brak zapisu; nie udawać, że dokumentacja została zaktualizowana.

### Dziennik zmian
| Data i czas (Europe/Warsaw) | Zdarzenie | Dokumentacja / dowód | Status |
|---|---|---|---|
| 2026-11-13 15:20 | Zgłoszono brak bieżącej aktualizacji dokumentacji po zmianach nieplanowanych. Dodano obowiązkowy protokół aktualizacji zdarzeniowej i weryfikacji zapisu. | Sekcja 13; commit `176b49124c2d63b8b1fd0186768c83003a4f1d82`; ponowny odczyt potwierdził zapis sekcji 13. | VERIFIED |
