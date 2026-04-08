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
    title = re.sub(r"(ΚΑΘΗΜΕΡΙΝΑ|ΣΑΒΒΑΤΟΚΥΡΙΑΚΟ|ΔΕΥΤΕΡΑ|ΤΡΙΤΗ|ΤΕΤΑΡΤΗ|ΠΕΜΠΤΗ|ΠΑΡΑΣΚΕΥΗ|ΣΑΒΒΑΤΟ|ΚΥΡΙΑΚΗ)\s*ΣΤΙΣ\s*\d{1,2}:\d{2}", "", title, flags=re.IGNORECASE)
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
            possible_time = match.group(1)
            if len(line.replace(possible_time, "").strip()) < 12:
                current_time = possible_time
                continue

        if current_time and len(line) > 3:
            title = clean_title(line)
            if title and len(title) > 2 and "Designed" not in title:
                programmes.append((current_time, title))
                current_time = None

    return programmes

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
                    if nh < h or (nh == h and nm < m):
                        stop_dt += timedelta(days=1)
                else:
                    stop_dt = start_dt + timedelta(hours=1)

                if h < 6:   # overnight
                    start_dt += timedelta(days=1)
                    stop_dt += timedelta(days=1)

                # Διόρθωση ίδιας ώρας (18:00-18:00)
                if (stop_dt - start_dt).total_seconds() < 60:
                    stop_dt = start_dt + timedelta(minutes=60)

                start_str = start_dt.strftime("%Y%m%d%H%M%S +0300")
                stop_str  = stop_dt.strftime("%Y%m%d%H%M%S +0300")

                xml += f'<programme channel="alpha.cy" start="{start_str}" stop="{stop_str}">\n'
                xml += f"  <title>{title}</title>\n</programme>\n"

            except:
                continue

    add_day(today_date)
    add_day(tomorrow_date)

    xml += "</tv>"

    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(xml)

    print(f"✅ Ενημερώθηκε με:")
    print(f"   → {today_date.strftime('%A %d/%m')} (σήμερα)")
    print(f"   → {tomorrow_date.strftime('%A %d/%m')} (αύριο)")

def main():
    now = datetime.now()
    today_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_date = today_date + timedelta(days=1)

    programmes = fetch_programmes()
    if programmes:
        build_xml(programmes, today_date, tomorrow_date)
    else:
        print("⚠️ Δεν βρέθηκαν προγράμματα.")

if __name__ == "__main__":
    main()
