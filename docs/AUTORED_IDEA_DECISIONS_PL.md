# AUTORED IDEA — decyzje architektoniczne

## ADR-001 — GitHub jako źródło wersjonowanej dokumentacji i kodu

**Status:** zaakceptowana  
**Decyzja:** używać istniejącego repozytorium `ElinaXproject/gpt` jako źródła kodu, dokumentacji, testów i historii zmian.  
**Powód:** dostępne uprawnienia zapisu, CI i historia commitów.  
**Konsekwencje:** nie przechowywać sekretów ani prywatnych plików mediów w publicznym repo.

## ADR-002 — jeden główny orkiestrator

**Status:** wstępna  
**Decyzja:** preferować Activepieces jako pierwszy kandydat ze względu na istniejący projekt i tabele; nie uruchamiać równolegle Activepieces i n8n dla tego samego procesu.  
**Warunek:** najpierw potwierdzić limity Cloud, dostępne połączenia i realny koszt kredytów; alternatywa self-hosted wymaga stałej infrastruktury, której jeszcze nie potwierdzono.  
**Konsekwencje:** nie budować produkcyjnych flow przed potwierdzeniem integracji i modelu kosztów.

## ADR-003 — oficjalne API i adaptery platformowe

**Status:** zaakceptowana  
**Decyzja:** TikTok przez oficjalny Content Posting API lub dostawcę z legalnym dostępem; YouTube przez YouTube Data API/OAuth lub dostawcę.  
**Odrzucone:** nieoficjalne API, automatyzacja przeglądarki omijająca zasady, obchodzenie limitów.  
**Konsekwencje:** wymagane zatwierdzenia, autoryzacje i testy kontraktowe.

## ADR-004 — brak płatnych zależności krytycznych

**Status:** zaakceptowana  
**Decyzja:** system podstawowy nie może zależeć od płatnego API, abonamentu, karty ani ukrytych opłat.  
**Konsekwencje:** darmowe limity będą jawnie mierzone; gdy się skończą, kolejka przechodzi w bezpieczny fallback zamiast omijać limity.

## ADR-005 — publikacja oddzielona od generowania

**Status:** zaakceptowana  
**Decyzja:** generowanie, walidacja, planowanie i publikacja to osobne moduły.  
**Powód:** ograniczenie ryzyka publikacji złej treści i duplikatów.  
**Konsekwencje:** adapter publikacyjny nie może przyjmować pakietu, który nie przeszedł walidacji.

## ADR-006 — idempotencja i state machine

**Status:** zaakceptowana  
**Decyzja:** każde zadanie publikacji ma deterministyczny klucz idempotencji i dozwolone przejścia stanów.  
**Implementacja:** `autored/core.py`; testy automatyczne w `tests/test_autored_core.py`.  
**Konsekwencje:** retry wymaga sprawdzenia stanu po stronie platformy.

## ADR-007 — retencja i backup

**Status:** wstępna  
**Decyzja:** nie uruchamiać Cloudflare R2 ani płatnego magazynu; zachować minimalizację mediów i zaprojektować szyfrowane, odseparowane backupy.  
**Warunek:** przed produkcją wskazać rzeczywiście dostępne bezpłatne miejsce i wykonać test odtworzenia.  
**Konsekwencje:** backup danych produkcyjnych jest obecnie BLOCKED.
