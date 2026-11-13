# AUTORED IDEA — renderer i produkcja mediów

**Wersja:** 0.1  
**Data:** 2026-11-13  
**Status:** IMPLEMENTED / SMOKE TEST PENDING

## 1. Renderer wideo

Plik: `scripts/render_vertical_video.py`

- Wejście: JSON z tytułem, skryptem, CTA i opcjonalną ścieżką do tła.
- Narracja: lokalny Piper TTS, domyślnie `pl_PL-darkman-medium`.
- Napisy: SRT tworzone z segmentów tekstu.
- Obraz: pionowe 1080×1920, 30 FPS; tło programowe lub przekazany obraz.
- Wideo: H.264 / yuv420p; audio AAC, 48 kHz, stereo.
- Normalizacja audio: FFmpeg loudnorm, cel -16 LUFS.
- Walidacja końcowa: FFprobe sprawdza kodeki, wymiary i czas trwania.
- Długość narracji: 5–90 sekund; poza zakresem renderer odrzuca zadanie.

## 2. Głos i licencje

Wybrano `pl_PL-darkman-medium`:
- polski głos Piper;
- oficjalna dokumentacja Piper Commercial Use wymienia ten wariant jako CC0 i dopuszczony do użycia komercyjnego;
- nie używać automatycznie `pl_PL-gosia-medium` do treści komercyjnych: jej łańcuch treningowy wymaga osobnej oceny;
- silnik Piper ma licencję GPL-3.0-or-later; pliki głosów mają odrębne licencje, które trzeba czytać w `MODEL_CARD`.

Źródła:
- https://github.com/OHF-Voice/piper1-gpl
- https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/LICENSING.md
- https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/COMMERCIAL_USE.md
- https://huggingface.co/rhasspy/piper-voices/tree/main/pl/pl_PL/darkman/medium
- https://pypi.org/project/piper-tts/ (wersja przypięta: 1.8.0)

## 3. Muzyka

- TikTok photo posts: Publora `autoAddMusic=true`, tylko gdy funkcja jest dostępna i dozwolona na koncie.
- TikTok video posts: renderer wymaga pliku muzycznego oraz niepustego `music_license_ref`, jeśli pakiet oznacza `platform=tiktok` i `format=video`.
- YouTube: muzyka opcjonalna; używać wyłącznie plików z udokumentowaną licencją.
- Brak licencji = blokada renderowania z muzyką. Nie pobierać utworów z nieautoryzowanych źródeł.

## 4. Obrazy AI

Wykonano test modelu Cloudflare Workers AI:
- `@cf/black-forest-labs/flux-1-schnell`;
- 4 kroki;
- wynik: obraz JPEG Base64, ok. 247 KB;
- darmowy limit Workers AI: 10 000 neuronów dziennie łącznie dla wszystkich modeli; po przekroczeniu limitu na Free kolejne wywołania mają być odrzucane.

Test nie oznacza jeszcze automatycznej integracji obrazu z rendererem. Obraz jest generowany przez API, ale nie ma jeszcze bezpiecznego kanału przekazania go do pipeline'u FFmpeg.

## 5. Smoke test

Workflow: `.github/workflows/render-smoke.yml`

Zakres:
1. instalacja FFmpeg;
2. instalacja przypiętego Piper TTS;
3. pobranie głosu i sprawdzenie jego karty licencyjnej;
4. render testowego filmu;
5. kontrola FFprobe;
6. zapis artefaktu na 7 dni.

Status: oczekuje na zakończenie GitHub Actions. Nie uznawać renderera za VERIFIED przed pozytywnym testem i odsłuchem próbki.
