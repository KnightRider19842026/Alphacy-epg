import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import xml.etree.ElementTree as ET
import os

URL = "https://www.alphacyprus.com.cy/program"
XML_FILE = "epg.xml"

# ---------------- FIXED DURATIONS (λεπτά) ----------------
FIX_DURATIONS = {
    "ALPHA ΚΑΛΗΜΕΡΑ": 90,
    "ALPHA ΕΝΗΜΕΡΩΣΗ": 150,
    "DEAL": 60,
    "ALPHA NEWS": 60,
    "ΟΙΚΟΓΕΝΕΙΑΚΕΣ ΙΣΤΟΡΙΕΣ": 60,
    "ΤΟ ΣΟΪ ΣΟΥ": 65,
    "ΜΕ ΑΓΑΠΗ ΧΡΙΣΤΙΑΝΑ": 60,
    "THE CHASE GREECE": 55,
    "ΑΓΙΟΣ ΠΑΪΣΙΟΣ - ΑΠΟ ΤΑ ΦΑΡΑΣΑ ΣΤΟΝ ΟΥΡΑΝΟ": 150,
    "ΑΥΤΟΨΙΑ": 90,
}

# ---------------- CLEAN TITLE ----------------
def clean_title(title):
    title = re.sub(r"\(.*?\)", "", title)
    title = re.sub(r"live now", "", title, flags=re.IGNORECASE)
    title = re.sub(r"Δες όλα τα επεισόδια στο WEBTV", "", title, flags=re.IGNORECASE)
    title = re.sub(r"copyright.*", "", title, flags=re.IGNORECASE)
    title = re.sub(
        r"(ΚΑΘΗΜΕΡΙΝΑ|ΣΑΒΒΑΤΟΚΥΡΙΑΚΟ|ΔΕΥΤΕΡΑ|ΤΡΙΤΗ|ΤΕΤΑΡΤΗ|ΠΕΜΠΤΗ|ΠΑΡΑΣΚΕΥΗ|ΣΑΒΒΑΤΟ|ΚΥΡΙΑΚΗ).*?\d{1,2}:\d{2}",
        "",
        title,
        flags=re.IGNORECASE
    )
    return re.sub(r"\s+", " ", title).strip()

# ---------------- FETCH DAY ----------------
def fetch_day_programmes(day_offset):
    resp = requests.get(URL, timeout=10)
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
            if title:
                programmes.append((current_time, title))
            current_time = None

    target_date = datetime.now() + timedelta(days=day_offset)
    return programmes, target_date

# ---------------- LOAD EXISTING ----------------
def load_existing():
    if not os.path.exists(XML_FILE):
        return []
    tree = ET.parse(XML_FILE)
    root = tree.getroot()
    data = []
    for prog in root.findall("programme"):
        data.append((
            prog.attrib["start"],
            prog.attrib["stop"],
            prog.find("title").text
        ))
    return data

# ---------------- MERGE ----------------
def merge_programmes(days_programmes):
    existing = load_existing()
    new_entries = []

    for programmes, target_date in days_programmes:
        target_day = target_date.strftime("%Y%m%d")
        # Remove old programmes of the same day
        existing = [x for x in existing if not x[0].startswith(target_day)]
        base_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)

        for i, (time_str, title) in enumerate(programmes):
            h, m = map(int, time_str.split(":"))
            start_dt = base_date + timedelta(hours=h, minutes=m)

            # fixed duration if exists
            if title in FIX_DURATIONS:
                stop_dt = start_dt + timedelta(minutes=FIX_DURATIONS[title])
            else:
                # default: μέχρι το επόμενο πρόγραμμα ή +120 λεπτά
                if i < len(programmes) - 1:
                    nh, nm = map(int, programmes[i + 1][0].split(":"))
                    stop_dt = base_date + timedelta(hours=nh, minutes=nm)
                    if stop_dt <= start_dt:
                        stop_dt += timedelta(days=1)
                else:
                    stop_dt = start_dt + timedelta(minutes=120)

            start = start_dt.strftime("%Y%m%d%H%M%S +0300")
            stop = stop_dt.strftime("%Y%m%d%H%M%S +0300")
            new_entries.append((start, stop, title))

    # Combine old + new
    all_data = existing + new_entries

    # Keep last 3 days only
    valid_days = sorted({x[0][:8] for x in all_data})[-3:]
    filtered = [x for x in all_data if x[0][:8] in valid_days]

    # Remove duplicates & sort
    unique = {}
    for item in filtered:
        unique[item[0]] = item
    final = sorted(unique.values(), key=lambda x: x[0])
    return final

# ---------------- SAVE ----------------
def save_xml(programmes):
    root = ET.Element("tv")
    channel = ET.SubElement(root, "channel", id="alpha.cy")
    display = ET.SubElement(channel, "display-name")
    display.text = "Alpha Cyprus"

    for start, stop, title in programmes:
        prog = ET.SubElement(root, "programme", channel="alpha.cy", start=start, stop=stop)
        t = ET.SubElement(prog, "title")
        t.text = title

    tree = ET.ElementTree(root)
    tree.write(XML_FILE, encoding="utf-8", xml_declaration=True)

# ---------------- MAIN ----------------
def main():
    try:
        # Φτιάχνουμε λίστα με 3 μέρες (σήμερα, αύριο, μεθεπόμενη)
        days_programmes = []
        for offset in range(3):
            prog, date = fetch_day_programmes(offset)
            days_programmes.append((prog, date))

        merged = merge_programmes(days_programmes)
        save_xml(merged)
        print(f"✅ OK - {len(merged)} programmes (3ήμερο με fixed durations)")
    except Exception as e:
        print("❌ ERROR:", e)

if __name__ == "__main__":
    main()
