from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
import re
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = "cyberbezpieczenstwo-secret-key-2024"

DATA_FILE = "tickets.json"



def load_tickets():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_tickets(tickets):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tickets, f, ensure_ascii=False, indent=2)



def classify_ticket_with_ai(title, description, category):
    """Call Claude to classify ticket priority and get analysis."""
    import urllib.request
    import json as _json

    prompt = f"""Jesteś ekspertem ds. cyberbezpieczeństwa. Przeanalizuj zgłoszony incydent i zwróć odpowiedź TYLKO jako JSON (bez żadnego dodatkowego tekstu, bez markdown).

Tytuł incydentu: {title}
Kategoria: {category}
Opis: {description}

Zwróć JSON w dokładnie tym formacie:
{{
  "priorytet": "KRYTYCZNY" | "WYSOKI" | "ŚREDNI" | "NISKI",
  "poziom_liczbowy": <liczba 1-4, gdzie 4=KRYTYCZNY>,
  "uzasadnienie": "<krótkie uzasadnienie po polsku, max 2 zdania>",
  "zalecane_dzialanie": "<konkretna rekomendacja po polsku, max 2 zdania>",
  "czas_reakcji": "<np. Natychmiast, 1 godzina, 4 godziny, 24 godziny>"
}}"""

    payload = _json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = _json.loads(resp.read().decode("utf-8"))

    raw = data["content"][0]["text"].strip()
    # strip possible ```json fences
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"```$", "", raw).strip()
    return _json.loads(raw)




@app.route("/")
def index():
    role = session.get("role", "pracownik")
    return render_template("index.html", role=role)

@app.route("/set-role/<role>")
def set_role(role):
    if role in ("pracownik", "administrator"):
        session["role"] = role
    return redirect(url_for("index"))

@app.route("/api/tickets", methods=["GET"])
def get_tickets():
    tickets = load_tickets()
    sort_by = request.args.get("sort", "data_utworzenia")
    order   = request.args.get("order", "desc")
    filter_priority = request.args.get("priorytet", "")
    filter_status   = request.args.get("status", "")
    filter_category = request.args.get("kategoria", "")

    if filter_priority:
        tickets = [t for t in tickets if t.get("priorytet") == filter_priority]
    if filter_status:
        tickets = [t for t in tickets if t.get("status") == filter_status]
    if filter_category:
        tickets = [t for t in tickets if t.get("kategoria") == filter_category]

    priority_order = {"KRYTYCZNY": 4, "WYSOKI": 3, "ŚREDNI": 2, "NISKI": 1}

    if sort_by == "priorytet":
        tickets.sort(key=lambda x: priority_order.get(x.get("priorytet", "NISKI"), 0),
                     reverse=(order == "desc"))
    elif sort_by == "data_utworzenia":
        tickets.sort(key=lambda x: x.get("data_utworzenia", ""),
                     reverse=(order == "desc"))
    elif sort_by == "tytul":
        tickets.sort(key=lambda x: x.get("tytul", "").lower(),
                     reverse=(order == "desc"))

    return jsonify(tickets)

@app.route("/api/tickets", methods=["POST"])
def create_ticket():
    data = request.json
    tickets = load_tickets()

    title       = data.get("tytul", "")
    description = data.get("opis", "")
    category    = data.get("kategoria", "")
    reporter    = data.get("zglaszajacy", "Anonim")

    # AI classification
    try:
        ai_result = classify_ticket_with_ai(title, description, category)
        priorytet          = ai_result.get("priorytet", "ŚREDNI")
        poziom_liczbowy    = ai_result.get("poziom_liczbowy", 2)
        uzasadnienie       = ai_result.get("uzasadnienie", "")
        zalecane_dzialanie = ai_result.get("zalecane_dzialanie", "")
        czas_reakcji       = ai_result.get("czas_reakcji", "")
        ai_error           = None
    except Exception as e:
        priorytet          = "ŚREDNI"
        poziom_liczbowy    = 2
        uzasadnienie       = "Błąd klasyfikacji AI – przypisano priorytet domyślny."
        zalecane_dzialanie = "Sprawdź ręcznie i zaktualizuj priorytet."
        czas_reakcji       = "4 godziny"
        ai_error           = str(e)

    ticket = {
        "id":                  str(uuid.uuid4())[:8].upper(),
        "tytul":               title,
        "opis":                description,
        "kategoria":           category,
        "zglaszajacy":         reporter,
        "priorytet":           priorytet,
        "poziom_liczbowy":     poziom_liczbowy,
        "uzasadnienie":        uzasadnienie,
        "zalecane_dzialanie":  zalecane_dzialanie,
        "czas_reakcji":        czas_reakcji,
        "status":              "Otwarte",
        "data_utworzenia":     datetime.now().isoformat(),
        "data_aktualizacji":   datetime.now().isoformat(),
        "komentarze":          [],
        "ai_error":            ai_error
    }

    tickets.append(ticket)
    save_tickets(tickets)
    return jsonify(ticket), 201

@app.route("/api/tickets/<ticket_id>", methods=["PATCH"])
def update_ticket(ticket_id):
    data    = request.json
    tickets = load_tickets()

    for ticket in tickets:
        if ticket["id"] == ticket_id:
            allowed = ["status", "priorytet", "przypisany_do"]
            for key in allowed:
                if key in data:
                    ticket[key] = data[key]
            ticket["data_aktualizacji"] = datetime.now().isoformat()
            save_tickets(tickets)
            return jsonify(ticket)

    return jsonify({"error": "Nie znaleziono ticketu"}), 404

@app.route("/api/tickets/<ticket_id>/komentarz", methods=["POST"])
def add_comment(ticket_id):
    data    = request.json
    tickets = load_tickets()

    for ticket in tickets:
        if ticket["id"] == ticket_id:
            comment = {
                "autor":   data.get("autor", "Administrator"),
                "tresc":   data.get("tresc", ""),
                "data":    datetime.now().isoformat()
            }
            ticket.setdefault("komentarze", []).append(comment)
            ticket["data_aktualizacji"] = datetime.now().isoformat()
            save_tickets(tickets)
            return jsonify(comment), 201

    return jsonify({"error": "Nie znaleziono ticketu"}), 404

@app.route("/api/stats", methods=["GET"])
def get_stats():
    tickets = load_tickets()
    stats = {
        "total":       len(tickets),
        "krytyczne":   sum(1 for t in tickets if t.get("priorytet") == "KRYTYCZNY"),
        "wysokie":     sum(1 for t in tickets if t.get("priorytet") == "WYSOKI"),
        "srednie":     sum(1 for t in tickets if t.get("priorytet") == "ŚREDNI"),
        "niskie":      sum(1 for t in tickets if t.get("priorytet") == "NISKI"),
        "otwarte":     sum(1 for t in tickets if t.get("status") == "Otwarte"),
        "w_toku":      sum(1 for t in tickets if t.get("status") == "W toku"),
        "zamkniete":   sum(1 for t in tickets if t.get("status") == "Zamknięte"),
    }
    return jsonify(stats)

if __name__ == "__main__":
    # Seed demo tickets if empty
    if not os.path.exists(DATA_FILE):
        demo = [
            {
                "id": "A1B2C3D4",
                "tytul": "Podejrzana aktywność na koncie administratora",
                "opis": "Wykryto logowania z nieznanych adresów IP między 2:00 a 4:00 w nocy.",
                "kategoria": "Naruszenie konta",
                "zglaszajacy": "Jan Kowalski",
                "priorytet": "KRYTYCZNY",
                "poziom_liczbowy": 4,
                "uzasadnienie": "Nieautoryzowane logowania na konto administratora stanowią poważne zagrożenie bezpieczeństwa.",
                "zalecane_dzialanie": "Natychmiast zablokować konto i przeprowadzić audyt dostępów.",
                "czas_reakcji": "Natychmiast",
                "status": "Otwarte",
                "data_utworzenia": "2025-05-01T08:23:00",
                "data_aktualizacji": "2025-05-01T08:23:00",
                "komentarze": [],
                "ai_error": None
            },
            {
                "id": "E5F6G7H8",
                "tytul": "Phishing – fałszywy e-mail od działu IT",
                "opis": "Pracownicy otrzymali wiadomość proszącą o podanie danych logowania pod pretekstem aktualizacji systemu.",
                "kategoria": "Phishing",
                "zglaszajacy": "Anna Nowak",
                "priorytet": "WYSOKI",
                "poziom_liczbowy": 3,
                "uzasadnienie": "Atak phishingowy może prowadzić do wycieku poświadczeń wielu pracowników.",
                "zalecane_dzialanie": "Wysłać ostrzeżenie do wszystkich pracowników i zablokować nadawcę.",
                "czas_reaktji": "1 godzina",
                "czas_reakcji": "1 godzina",
                "status": "W toku",
                "data_utworzenia": "2025-05-02T10:11:00",
                "data_aktualizacji": "2025-05-02T11:00:00",
                "komentarze": [
                    {"autor": "Admin", "tresc": "Zidentyfikowano nadawcę – domena zewnętrzna.", "data": "2025-05-02T11:00:00"}
                ],
                "ai_error": None
            },
            {
                "id": "I9J0K1L2",
                "tytul": "Wyciek danych klientów – baza danych CRM",
                "opis": "Odkryto publicznie dostępny endpoint API zwracający dane osobowe klientów bez autoryzacji.",
                "kategoria": "Wyciek danych",
                "zglaszajacy": "Piotr Wiśniewski",
                "priorytet": "KRYTYCZNY",
                "poziom_liczbowy": 4,
                "uzasadnienie": "Publiczny dostęp do danych osobowych narusza RODO i może skutkować poważnymi konsekwencjami prawnymi.",
                "zalecane_dzialanie": "Natychmiast wyłączyć endpoint i przeprowadzić analizę zakresu wycieku.",
                "czas_reakcji": "Natychmiast",
                "status": "Otwarte",
                "data_utworzenia": "2025-05-02T14:55:00",
                "data_aktualizacji": "2025-05-02T14:55:00",
                "komentarze": [],
                "ai_error": None
            },
            {
                "id": "M3N4O5P6",
                "tytul": "Nieaktualne oprogramowanie antywirusowe na stacjach",
                "opis": "Na 15 stacjach roboczych wykryto nieaktualne sygnatury antywirusowe (ponad 30 dni).",
                "kategoria": "Podatność systemu",
                "zglaszajacy": "Marta Zielińska",
                "priorytet": "ŚREDNI",
                "poziom_liczbowy": 2,
                "uzasadnienie": "Nieaktualne oprogramowanie zwiększa ryzyko infekcji złośliwym oprogramowaniem.",
                "zalecane_dzialanie": "Przeprowadzić aktualizację sygnatur na wszystkich stacjach roboczych.",
                "czas_reakcji": "4 godziny",
                "status": "Otwarte",
                "data_utworzenia": "2025-05-03T09:00:00",
                "data_aktualizacji": "2025-05-03T09:00:00",
                "komentarze": [],
                "ai_error": None
            },
            {
                "id": "Q7R8S9T0",
                "tytul": "Użytkownik zgłasza spowolnienie pracy komputera",
                "opis": "Pracownik zgłasza, że komputer działa wolniej niż zwykle od kilku dni.",
                "kategoria": "Inne",
                "zglaszajacy": "Tomasz Kaczmarek",
                "priorytet": "NISKI",
                "poziom_liczbowy": 1,
                "uzasadnienie": "Spowolnienie może być spowodowane wieloma czynnikami niezwiązanymi z bezpieczeństwem.",
                "zalecane_dzialanie": "Przeprowadzić skan antywirusowy i sprawdzić procesy systemowe.",
                "czas_reakcji": "24 godziny",
                "status": "Zamknięte",
                "data_utworzenia": "2025-04-30T15:30:00",
                "data_aktualizacji": "2025-05-01T10:00:00",
                "komentarze": [
                    {"autor": "Admin", "tresc": "Problem rozwiązany – usunięto zbędne procesy i zaktualizowano system.", "data": "2025-05-01T10:00:00"}
                ],
                "ai_error": None
            }
        ]
        save_tickets(demo)

    app.run(debug=True, port=5004)
