# SecureDesk – System Zarządzania Incydentami Bezpieczeństwa

Projekt zaliczeniowy z przedmiotu **Cyberbezpieczeństwo**.

## Opis

Aplikacja webowa do zarządzania zgłoszeniami incydentów bezpieczeństwa (ticketing system) z automatyczną klasyfikacją priorytetu przez sztuczną inteligencję (Claude AI).

## Funkcjonalności

### Dla Pracownika
- Wypełnianie formularza zgłoszenia incydentu (tytuł, opis, kategoria, imię)
- Automatyczna klasyfikacja priorytetu przez AI (KRYTYCZNY / WYSOKI / ŚREDNI / NISKI)
- Podgląd szczegółów każdego zgłoszenia

### Dla Administratora
- Lista wszystkich zgłoszeń (do ~200 jednocześnie)
- Sortowanie według: priorytetu, daty, tytułu
- Filtrowanie według: priorytetu, statusu, kategorii
- Zmiana statusu ticketu (Otwarte / W toku / Zamknięte)
- Dodawanie komentarzy do zgłoszeń
- Ręczna zmiana priorytetu
- Statystyki na górze strony

### AI (Claude Sonnet)
- Analiza tytułu, opisu i kategorii incydentu
- Przypisanie priorytetu z uzasadnieniem
- Zalecenie konkretnego działania
- Określenie wymaganego czasu reakcji

## Uruchomienie

```bash
# Zainstaluj zależności
pip install flask

# Uruchom aplikację
python app.py
```

Otwórz przeglądarkę: http://localhost:5000

## Technologie

- **Backend**: Python 3 + Flask
- **Frontend**: HTML5 / CSS3 / Vanilla JavaScript
- **AI**: Anthropic Claude Sonnet (REST API)
- **Baza danych**: JSON (tickets.json)

## Kategorie incydentów

- Phishing
- Wyciek danych
- Naruszenie konta
- Malware
- Atak DDoS
- Nieautoryzowany dostęp
- Podatność systemu
- Inne

## Poziomy priorytetu

| Poziom | Nazwa | Czas reakcji |
|--------|-------|-------------|
| 4 | KRYTYCZNY | Natychmiast |
| 3 | WYSOKI | 1 godzina |
| 2 | ŚREDNI | 4 godziny |
| 1 | NISKI | 24 godziny |
