# AUTORED IDEA — plan testów i kryteria odbioru

**Wersja:** 0.1  
**Data:** 2026-11-13  
**Status:** plan testów; żaden test produkcyjnej publikacji nie jest jeszcze zaliczony

## 1. Zasada testowania

Każdy etap przechodzi:
1. test jednostkowy modułu;
2. test integracji z bezpośrednim poprzednikiem i następnym modułem;
3. test regresji krytycznych ścieżek;
4. niezależny odczyt wyniku z systemu docelowego;
5. wpis do dziennika z dowodem i statusem PASS / FAIL / BLOCKED / NOT RUN.

Nie wykonywać realnej publikacji publicznej w testach. Używać mocków, prywatności testowej lub zatwierdzonego kanału testowego. Nigdy nie uznawać samego HTTP 200 za dowód opublikowania.

## 2. Macierz testów

| ID | Obszar | Scenariusz | Oczekiwany rezultat | Status 2026-11-13 |
|---|---|---|---|---|
| T01 | Profil | konto docelowe nieznane | zadanie zablokowane | NOT RUN |
| T02 | Treść | brak tytułu/opisu dla formatu wymagającego | walidacja odrzuca | NOT RUN |
| T03 | Research | twierdzenie bez wiarygodnego źródła | brak przejścia do publikacji | NOT RUN |
| T04 | Media | nieobsługiwany MIME | odrzucenie przed uploadem | NOT RUN |
| T05 | Media | plik za duży | odrzucenie z czytelnym błędem | NOT RUN |
| T06 | Media | zła proporcja / rozdzielczość | odrzucenie lub kontrolowana konwersja | NOT RUN |
| T07 | Media | plik uszkodzony | FFprobe / decode test fail | NOT RUN |
| T08 | AI disclosure | materiał AI bez wymaganej deklaracji | blokada publikacji | NOT RUN |
| T09 | Copyright | brak dowodu licencji audio/wideo | blokada publikacji | NOT RUN |
| T10 | Idempotencja | ten sam job uruchomiony 2 razy | jedna publikacja | NOT RUN |
| T11 | Retry | timeout po stronie dostawcy | reconciliation przed retry | NOT RUN |
| T12 | Quota | limit wyczerpany | kolejka/fallback, bez pętli | NOT RUN |
| T13 | OAuth | token wygasł | bezpieczne zatrzymanie i alert | NOT RUN |
| T14 | TikTok | nieaudytowana aplikacja | status prywatny i brak publicznego sukcesu | NOT RUN |
| T15 | YouTube | OAuth bez youtube.upload | błąd scope, brak uploadu | NOT RUN |
| T16 | Publikacja | API przyjmuje upload | polling statusu aż do terminalnego stanu | NOT RUN |
| T17 | Rejestr | post opublikowany | zapis platform_post_id i URL | NOT RUN |
| T18 | Regresja | błąd jednego profilu | pozostałe profile nadal działają | NOT RUN |
| T19 | Backup | uszkodzony plik backupu | test integralności wykrywa błąd | NOT RUN |
| T20 | DR | odtworzenie do staging | spójność rekordów i hashy | NOT RUN |
| T21 | Sekrety | token w logu/artefakcie | test bezpieczeństwa fail | NOT RUN |
| T22 | Scheduler | awaria workera podczas renderu | wznowienie bez duplikatu | NOT RUN |
| T23 | Safety | treść nie przechodzi kontroli bezpieczeństwa | publikacja zablokowana | NOT RUN |

## 3. Kryteria jakości treści

- poprawność językowa i zgodność z tonem konkretnego konta;
- brak powtarzania identycznego tematu/obrazu w ustalonym oknie;
- sprawdzalne źródła dla treści faktograficznych;
- brak nieudokumentowanych statystyk i cytatów;
- poprawne CTA i hashtagi, bez obietnic zasięgów;
- prawidłowe AI disclosure;
- brak cudzych znaków wodnych i nieautoryzowanej muzyki;
- prawidłowy format, kodek, proporcja, długość i rozmiar;
- zgodność metadanych z docelową platformą.

## 4. Kryteria akceptacji całego systemu

System może otrzymać status PRODUCTION VERIFIED dopiero, gdy:
- wszystkie trzy konta są jednoznacznie zmapowane i autoryzowane;
- generowanie materiałów dla każdego konta działa w oddzielnym kontekście;
- wszystkie T01–T22 są PASS lub udokumentowany wyjątek nie dotyczy zakresu;
- każdy adapter publikacji przeszedł test i potwierdził status końcowy;
- nie ma duplikatów po retry i timeout;
- limity są odczytywane i respektowane;
- monitoring i alerty działają;
- backup i test odtworzenia są VERIFIED;
- dokumentacja odzwierciedla rzeczywisty stan;
- publikacja publiczna jest aktywowana tylko dla skonfigurowanych kont i ustawień.

## 5. Testy integracyjne obowiązkowe po każdym etapie

| Po etapie | Test przekrojowy |
|---|---|
| Planowanie | profil → kalendarz → deduplikacja |
| Generowanie tekstu | źródła → skrypt → tytuł/opis/hashtagi |
| Renderowanie | skrypt → media → FFprobe → hash |
| Walidacja | media + prawa + disclosure + metadane |
| Publikacja | quota → idempotency → adapter → status |
| Monitoring | zdarzenie → log → alert → procedura naprawy |
| Backup | zapis → kopia → restore → porównanie |
