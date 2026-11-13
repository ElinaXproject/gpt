# AUTORED IDEA — bezpieczne uruchomienie integracji Publora

## Cel
Ten dokument opisuje jedyne ręczne czynności wymagane do uruchomienia bezpiecznego testu integracji. Workflow preflight jest wyłącznie odczytowy: sprawdza połączenia i tokeny, nie tworzy szkiców, nie planuje i nie publikuje.

## 1. Wymagany sekret API
1. Zaloguj się do własnego konta Publora i utwórz klucz API w sekcji API.
2. Nie wklejaj klucza do rozmowy, kodu, pliku JSON, issue ani logów.
3. W repozytorium GitHub `ElinaXproject/gpt` otwórz Settings → Secrets and variables → Actions → New repository secret.
4. Nazwa sekretu musi być dokładnie `PUBLORA_API_KEY`.
5. Wartością jest klucz utworzony w Publora.

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
- sprawdzi dokładne uchwyty i stan połączeń,
- sprawdzi YouTube channel ID,
- wywoła test połączenia dostawcy,
- nie utworzy posta i nie wykona publikacji.

Wymagany wynik: `status: ready`, `ready_profiles: 3`.

## 4. Limity darmowego planu
Według aktualnej dokumentacji Publora Starter obejmuje 3 konta, 15 publikacji miesięcznie, maksymalnie 3 zaplanowane posty naraz i horyzont 7 dni. Nie zakładać, że wystarczy to do codziennej publikacji na wszystkich profilach. Nie włączać płatnego planu ani nie dodawać metody płatności w ramach tego projektu.

## 5. Bramka bezpieczeństwa
Do czasu przejścia preflight:
- nie uruchamiać automatycznej publikacji,
- nie używać Metricool dla YouTube,
- nie tworzyć postów testowych na profilach publicznych,
- nie umieszczać sekretów w repozytorium,
- nie omijać limitów, OAuth, audytu ani zasad platform.

Źródła techniczne:
- https://docs.publora.com/getting-started
- https://docs.publora.com/endpoints/platform-connections
- https://docs.publora.com/endpoints/create-post
- https://docs.publora.com/endpoints/upload-media
