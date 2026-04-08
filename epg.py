import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import xml.etree.ElementTree as ET
import os

URL = "https://www.alphacyprus.com.cy/program"
XML_FILE = "epg.xml"

# ---------------- CLEAN TITLE ----------------
def clean_title(title):
    title = re.sub(r"\(.*?\)", "", title)
    title = re.sub(r"live now", "", title, flags=re.IGNORECASE)
    title = re.sub(r"Δες όλα τα επεισόδια στο WEBTV", "", title, flags=re.IGNORECASE)
    title = re.sub(r"copyright.*", "", title, flags=re.IGNORECASE)
    title = re.sub(
        r"(ΚΑΘΗΜΕΡΙΝΑ|ΣΑΒΒΑΤΟΚΥΡΙΑΚΟ|ΔΕΥΤΕΡΑ|ΤΡΙΤΗ|ΤΕΤΑΡΤΗ|ΠΕΜΠΤΗ|ΠΑΡΑΣΚΕΥΗ|ΣΑΒΒΑΤΟ|ΚΥΡΙΑΚΗ).*?\d{1,2}:\d{2}",
        "", title, flags=re.IGNORECASE
    )
    return re.sub(r"\s+", " ", title).strip()

# ---------------- FETCH NEXT DAY ----------------
def fetch_next_day_programmes():
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

    tomorrow = datetime.now() + timedelta(days=1)
    return programmes, tomorrow

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
def merge_programmes(new_programmes, target_date):
    existing = load_existing()

    target_day = target_date.strftime("%Y%m%d")

    # 🔥 IMPORTANT FIX → overwrite ίδιας μέρας
    existing = [x for x in existing if not x[0].startswith(target_day)]

    base_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)

    new_entries = []

    for i, (time_str, title) in enumerate(new_programmes):
        h, m = map(int, time_str.split(":"))
        start_dt = base_date + timedelta(hours=h, minutes=m)

        if i < len(new_programmes) - 1:
    nh, nm = map(int, new_programmes[i + 1][0].split(":"))
    stop_dt = base_date + timedelta(hours=nh, minutes=nm)

    # 🔥 FIX: αν πάει πίσω → είναι επόμενη μέρα
    if stop_dt <= start_dt:
        stop_dt += timedelta(days=1)
        else:
    stop_dt = start_dt + timedelta(minutes=120)  # πιο safe

        start = start_dt.strftime("%Y%m%d%H%M%S +0300")
        stop = stop_dt.strftime("%Y%m%d%H%M%S +0300")

        new_entries.append((start, stop, title))

    # 🔥 κράτα μόνο 3 μέρες
    now = datetime.now()
    cutoff = now - timedelta(days=2)

    filtered = []
    for start, stop, title in existing:
        dt = datetime.strptime(start[:14], "%Y%m%d%H%M%S")
        if dt >= cutoff:
            filtered.append((start, stop, title))

    all_data = filtered + new_entries

    # 🔥 remove duplicates
    unique = {}
    for item in all_data:
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
        new_programmes, target_date = fetch_next_day_programmes()

        if not new_programmes:
            print("❌ Δεν βρέθηκαν προγράμματα")
            return

        merged = merge_programmes(new_programmes, target_date)
        save_xml(merged)

        print(f"✅ OK - {len(merged)} programmes")

    except Exception as e:
        print("❌ ERROR:", e)

if __name__ == "__main__":
    main()
