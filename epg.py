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
    title = re.sub(r"(ΚΑΘΗΜΕΡΙΝΑ|ΣΑΒΒΑΤΟΚΥΡΙΑΚΟ).*?\d{1,2}:\d{2}", "", title, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", title).strip().strip('- ')

def fetch_programmes():
    resp = requests.get(URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    programmes = []
    time_pattern = re.compile(r"(\d{1,2}:\d{2})")

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    current_time = None
    for line in lines:
        match = time_pattern.search(line)
        if match:
            t = match.group(1)
            # Πολύ αυστηρός έλεγχος για γραμμές ώρας
            if len(line) < 20 and any(c.isdigit() for c in t):
                current_time = t
                continue

        if current_time and len(line) > 4:
            title = clean_title(line)
            if title and len(title) > 3 and "Designed" not in title:
                programmes.append((current_time, title))
                current_time = None

    # Αφαιρούμε διπλότυπες ώρες (σημαντικό για το 06:00)
    clean_prog = []
    seen_times = set()
    for t, title in programmes:
        if t not in seen_times:
            seen_times.add(t)
            clean_prog.append((t, title))
        elif title != clean_prog[-1][1]:   # αν είναι διαφορετικός τίτλος, κρατάμε και αυτόν
            clean_prog.append((t, title))

    return clean_prog

def build_xml(programmes, today_date, tomorrow_date):
    xml = '<?xml version="1.0" encoding="utf-8"?>\n<tv>\n'
    xml += '<channel id="alpha.cy">\n  <display-name>Alpha Cyprus</display-name>\n</channel>\n'

    def add_day(base_date):
        nonlocal xml
        for i, (time_str, title) in enumerate(programmes):
            try:
                h, m = map(int, time_str.split(":"))
                start_dt = base_date.replace(hour=h, minute=m, second=0, microsecond=0)

                if i < len(programmes) - 1:
                    nh, nm = map(int, programmes[i + 1][0].split(":"))
                    stop_dt = base_date.replace(hour=nh, minute=nm, second=0, microsecond=0)

                    # Overnight (23:xx → 01:xx)
                    if nh < h or (nh == h and nm < m):
                        stop_dt += timedelta(days=1)
                else:
                    stop_dt = start_dt + timedelta(hours=1)

                # Προγράμματα μετά τα μεσάνυχτα
                if h < 6:
                    start_dt += timedelta(days=1)
                    stop_dt += timedelta(days=1)

                # Διόρθωση λάθους διάρκειας (π.χ. 06:00-06:00)
                if (stop_dt - start_dt).total_seconds() < 300:   # λιγότερο από 5 λεπτά
                    stop_dt = start_dt + timedelta(minutes=60)

                start_str = start_dt.strftime("%Y%m%d%H%M%S +0300")
                stop_str  = stop_dt.strftime("%Y%m%d%H%M%S +0300")

                xml += f'<programme channel="alpha.cy" start="{start_str}" stop="{stop_str}">\n'
                xml += f"  <title>{title}</title>\n</programme>\n"

            except:
                continue

    # Μόνο οι 2 τελευταίες ημέρες (πολύ επιθετικό καθάρισμα)
    print(f"→ Προσθήκη {today_date.strftime('%A %d/%m')}")
    add_day(today_date)
    print(f"→ Προσθήκη {tomorrow_date.strftime('%A %d/%m')}")
    add_day(tomorrow_date)

    xml += "</tv>"

    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(xml)

    print(f"\n✅ epg.xml ενημερώθηκε επιτυχώς!")
    print(f"   Σήμερα : {today_date.strftime('%A %d/%m/%Y')}")
    print(f"   Αύριο  : {tomorrow_date.strftime('%A %d/%m/%Y')}")

def main():
    now = datetime.now()
    today_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_date = today_date + timedelta(days=1)

    programmes = fetch_programmes()
    print(f"Βρέθηκαν {len(programmes)} προγράμματα από την Alpha")

    if programmes:
        build_xml(programmes, today_date, tomorrow_date)
    else:
        print("⚠️ Δεν βρέθηκαν προγράμματα.")

if __name__ == "__main__":
    main()
