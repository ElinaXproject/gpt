# AUTORED IDEA — audyt adapterów publikacyjnych

**Data odczytu:** 2026-11-13 17:16 Europe/Warsaw  
**Typ:** read-only audit; nie tworzono ani nie publikowano postów.

## Publora

| Pole | Odczyt |
|---|---|
| Plan | Starter |
| Publikacje miesięczne | 15 |
| Wykorzystane w bieżącym okresie | 2 |
| Pozostało | 13 |
| Aktywne zaplanowane sloty | 0 / 3 |
| Maksymalny horyzont planowania | 7 dni |
| Połączenia | 1 / 3 |
| Dostępne funkcje | publishing, API access, MCP access |
| Analytics | niedostępne |

Połączenie:
- TikTok `@pieknemedia` — aktywne, token ważny.
- Pozostałe konta projektu nie są podłączone do Publora.

Konsekwencja dla planowania:
- nie zakładać codziennego publikowania na wszystkich kontach;
- miesięczny limit 15 dotyczy publikacji platformowych, a nie samych grup postów;
- limit kolejki 3 i horyzont 7 dni muszą być respektowane;
- przed każdym batch'em ponownie odczytać `account_context`; odczyt nie rezerwuje limitu.

## Metricool

Odczytano jeden brand:
- nazwa: `RED ABSURD IDEA`;
- strefa: `Europe/Warsaw`;
- połączenie TikTok `@ocenionona6`;
- połączenie YouTube z identyfikatorem kanału widocznym w Metricool; zgodność z handle `@MemoryAgent-r3c` wymaga jeszcze potwierdzenia;
- Metricool zwrócił także inne sieci, ale nie są częścią tego projektu.

Plan i limity publikacji Metricool nie są dostępne w odczytanych danych. Nie przyjmować żadnej liczby jako faktu i nie planować wykorzystania limitu, dopóki nie zostanie potwierdzony.

## Mapowanie profili projektu

| Profil | Provider | Status |
|---|---|---|
| TikTok `@pieknemedia` | Publora | CONNECTED |
| TikTok `@ocenionona6` | Metricool | CONNECTED |
| YouTube `@MemoryAgent-r3c` | Metricool | CHANNEL ID PRESENT; HANDLE NOT VERIFIED |

## Blokady integracyjne

1. Worker Cloudflare nie ma poświadczeń Publora ani Metricool.
2. Nie ma jeszcze adapterów produkcyjnych z testami kontraktowymi.
3. Nie wolno kopiować tokenów z połączeń ChatGPT do kodu ani repozytorium.
4. Poświadczenia należy dodać wyłącznie przez bezpieczny mechanizm sekretów providera, po autoryzacji właściciela konta.
5. YouTube musi zostać potwierdzony jako właściwy kanał `@MemoryAgent-r3c` przed pierwszym uploadem.
6. Każdy adapter musi używać idempotency key i po nieznanym wyniku sprawdzać stan posta przed ponowieniem.

## Reguły publikacji

- Publikacja publiczna pozostaje wyłączona do czasu przejścia testów E2E.
- Każdy pakiet musi mieć `safety_review_status=passed`, potwierdzone prawa do mediów i wymagane oznaczenie AI.
- TikTok photo posts: Publora `autoAddMusic=true`, jeśli funkcja jest dostępna dla połączenia.
- TikTok video posts: wymagany osadzony, licencjonowany podkład; brak potwierdzenia licencji blokuje publikację.
- Nie obchodzić limitów providerów ani ograniczeń platform.
