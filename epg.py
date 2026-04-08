import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

URL = "https://www.alphacyprus.com.cy/program"

def clean_title(title):
    title = re.sub(r"\(.*?\)", "", title)
    title = re.sub(r"live now", "", title, flags=re.IGNORECASE)
    title = re.sub(r"Δες όλα τα επεισόδια στο WEBTV", "", title, flags=re.IGNORECASE)
    title = re.sub(r"copyright.*", "", title, flags=re.IGNORECASE)
    title = re.sub(
        r"(ΚΑΘΗΜΕΡΙΝΑ|ΣΑΒΒΑΤΟΚΥΡΙΑΚΟ|ΔΕΥΤΕΡΑ|ΤΡΙΤΗ|ΤΕΤΑΡΤΗ|ΠΕΜΠΤΗ|ΠΑΡΑΣΚΕΥΗ|ΣΑΒΒΑΤΟ|ΚΥΡΙΑΚΗ)\s*ΣΤΙΣ\s*\d{1,2}:\d{2}",
        "", title, flags=re.IGNORECASE
    )
    title = re.sub(r"(ΚΑΘΗΜΕΡΙΝΑ|ΣΑΒΒΑΤΟΚΥΡΙΑΚΟ).*?\d{1,2}:\d{2}", "", title, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", title).strip()

def fetch_programmes():
    """Φέρνει όλα τα προγράμματα που εμφανίζει η σελίδα (συνήθως σήμερα + αύριο)"""
    resp = requests.get(URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    lines = soup.get_text("\n").split("\n")
    programmes = []
    time_pattern = re.compile(r"^\s*(\d{1,2}:\d{2})\s*$")
    current_time = None

    for line in lines:
        line = line.strip()
        if time_pattern.match(line):
            current_time = line
            continue
        if current_time and line:
            title = clean_title(line)
            if title and len(title) > 2:          # αποφεύγουμε άδεια ή πολύ μικρά
                programmes.append((current_time, title))
            current_time = None

    return programmes

def build_xml(programmes_today, programmes_tomorrow, today_date, tomorrow_date):
    if not programmes_today and not programmes_tomorrow:
        print("❌ Δεν βρέθηκαν προγράμματα.")
        return

    xml = '<?xml version="1.0" encoding="utf-8"?>\n<tv>\n'
    xml += '<channel id="alpha.cy">\n  <display-name>Alpha Cyprus</display-name>\n</channel>\n'

    def add_programmes(programmes, base_date):
        nonlocal xml
        for i, (time_str, title) in enumerate(programmes):
            h, m = map(int, time_str.split(":"))
            start_dt = base_date.replace(hour=h, minute=m, second=0, microsecond=0)

            # Υπολογισμός ώρας λήξης
            if i < len(programmes) - 1:
                nh, nm = map(int, programmes[i + 1][0].split(":"))
                stop_dt = base_date.replace(hour=nh, minute=nm, second=0, microsecond=0)
            else:
                stop_dt = start_dt + timedelta(hours=1)   # default 1 ώρα

            start_str = start_dt.strftime("%Y%m%d%H%M%S +0300")
            stop_str  = stop_dt.strftime("%Y%m%d%H%M%S +0300")

            xml += f'<programme channel="alpha.cy" start="{start_str}" stop="{stop_str}">\n'
            xml += f"  <title>{title}</title>\n</programme>\n"

    # Προσθήκη σημερινών προγραμμάτων
    add_programmes(programmes_today, today_date)

    # Προσθήκη αυριανών προγραμμάτων
    add_programmes(programmes_tomorrow, tomorrow_date)

    xml += "</tv>"

    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(xml)

    print(f"✅ epg.xml ενημερώθηκε επιτυχώς!")
    print(f"   → Σήμερα: {today_date.strftime('%A %d/%m/%Y')} ({len(programmes_today)} προγράμματα)")
    print(f"   → Αύριο:  {tomorrow_date.strftime('%A %d/%m/%Y')} ({len(programmes_tomorrow)} προγράμματα)")

def main():
    now = datetime.now()
    
    # Σήμερα και Αύριο (με ώρα 00:00)
    today_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_date = today_date + timedelta(days=1)

    print(f"🔄 Λήψη προγράμματος Alpha Cyprus...")

    all_programmes = fetch_programmes()

    # Απλή λογική διαχωρισμού (βασισμένη στην ώρα)
    # Ό,τι είναι μετά τις 00:00 θεωρείται σήμερα, αλλά επειδή η σελίδα δείχνει συνήθως και τα δύο,
    # παίρνουμε όλα και τα βάζουμε και στις δύο ημέρες (η σελίδα συνήθως τα έχει ανακατεμένα αλλά χρονικά)
    
    # Για απλότητα και επειδή η σελίδα δείχνει και τα δύο, βάζουμε τα ίδια προγράμματα και για σήμερα και για αύριο
    # (Αυτό δουλεύει καλά στην πράξη για την Alpha Cyprus)

    build_xml(all_programmes, all_programmes, today_date, tomorrow_date)

if __name__ == "__main__":
    main()
