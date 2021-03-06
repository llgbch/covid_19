#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import scrape_common as sc
from collections import defaultdict, OrderedDict
from datetime import datetime

main_url = "https://www.baselland.ch/politik-und-behorden/direktionen/volkswirtschafts-und-gesundheitsdirektion/amt-fur-gesundheit/medizinische-dienste/kantonsarztlicher-dienst/aktuelles/covid-19-faelle-kanton-basel-landschaft"
main_site = sc.download(main_url, silent=True)

# 2020-04-08, two iframes
"""
    <iframe width="100%" class="iframeblock loading" onload="onIframeLoaded(this)" src="https://www.statistik.bl.ch/files/sites/Grafiken/COVID19/20200407_COVID19_BL.htm" scrolling="auto" height="600"></iframe>
    <iframe width="100%" class="iframeblock loading" onload="onIframeLoaded(this)" src="https://www.statistik.bl.ch/files/sites/Grafiken/COVID19/20200407_COVID19_BL_Hosp.htm" scrolling="auto" height="600"></iframe>
"""


def parse_row_date(s):
    row_date = s.replace('-', '.')
    parts = row_date.split('.')
    s_date = datetime(day=int(parts[0]), month=int(parts[1]), year=int(parts[2]))
    return s_date.date().isoformat()


rows = defaultdict(dict)
soup = BeautifulSoup(main_site, 'html.parser')
for iframe in soup.find_all('iframe'):
    iframe_url = (iframe['src'])

    d = sc.download(iframe_url, silent=True)

    # 2020-07-29
    """
    <pre id="data_1" style="display:none; margin-top: 20px;">
    Datum,&quot;Personen in Isolation&quot;,&quot;Personen in Quarantäne (Tracing)&quot;,&quot;Personen in Quarantäne (Rückreise Risikoländer)&quot;
    11-05-2020,0.0,0.0,
    """

    d = d.replace('\n', ' ')

    # cases data
    data = sc.find(r'<pre id="data[^"]*".*?> ?Datum, Bestätigte Fälle, Geheilte (?:geschätzt|kalkuliert), (?:Verstorbene|Todesfälle)\s*([^<]+)</pre>', d)
    if data:
        continue

    # hospitalization data
    data = sc.find(r'<pre id="data[^"]*".*?> ?Datum, Normale Station, Intensivstation\s*([^<]+)</pre>', d)
    if data:
        continue

    # death and recovered data
    data = sc.find(r'<pre id="data[^"]*".*?> ?Datum, Geheilte kalkuliert, Aktive Fälle, Todesfälle\s*([^<]+)</pre>', d) or \
        sc.find(r'<pre id="data_1".*?> ?Datum,&quot;Geheilte \(kalkuliert\)&quot;,&quot;Aktive Fälle \(kalkuliert\)&quot;,&quot;Todesfälle&quot;\s*([^<]+)</pre>', d)
    if data:
        continue

    # hospitalization data
    data = sc.find(r'<pre id="data_1".*?> ?Datum,&quot;Normale Station&quot;,&quot;Intensivstation \(nicht beatmet\)&quot;,&quot;Intensivstation \(beatmet\)&quot;\s*([^<]+)</pre>', d)
    if data:
        continue

    # contact tracing data
    data = sc.find(r'<pre id="data_1".*?> ?Datum,&quot;Personen in Isolation&quot;,&quot;Personen in Quarantäne \(Tracing\)&quot;,&quot;Personen in Quarantäne \(Rückreise Risikoländer\)&quot;\s*([^<]+)</pre>', d)
    if data:
        continue

    # 14-Tage-Inzidenz Region
    data = sc.find(r'<pre id="data_1".*?> ?Datum,&quot;Inzidenz BL \(14-Tage\)&quot;,&quot;Inzidenz BS \(14-Tage\)&quot;,&quot;Inzidenz BS/BL/Dorneck/Thierstein \(14-Tage\)&quot;\s*([^<]+)</pre>', d)
    if data:
        continue

    # district data!
    data = sc.find(r'<pre id="data_1".*?> ?Datum,&quot;Bezirk Arlesheim&quot;,&quot;Bezirk Laufen&quot;,&quot;Bezirk Liestal&quot;,&quot;Bezirk Sissach&quot;,&quot;Bezirk Waldenburg&quot;\s*([^<]+)</pre>', d)
    if data:
        # take "Fallzahlen Bezirke BL ab Juni 2020", but not the 14d averaged one
        if iframe_url.find('/dbw/123') > 0:
            for row in data.split(" "):
                c = row.split(',')
                if len(c) == 6:
                    row_date = parse_row_date(c[0])
                    rows[row_date]['date'] = row_date
                    rows[row_date]['Arlesheim'] = int(c[1])
                    rows[row_date]['Laufen'] = int(c[2])
                    rows[row_date]['Liestal'] = int(c[3])
                    rows[row_date]['Sissach'] = int(c[4])
                    rows[row_date]['Waldenburg'] = int(c[5])
        continue

    # we should never reach here unless there is an unknown iframe
    raise Exception(f"issue parsing data in iframe {iframe_url}")

# https://www.bfs.admin.ch/bfs/de/home/statistiken/kataloge-datenbanken/karten.assetdetail.5688189.html
district_ids = {
    'Arlesheim': 1301,
    'Laufen': 1302,
    'Liestal': 1303,
    'Sissach': 1304,
    'Waldenburg': 1305,
}

# https://www.statistik.bl.ch/web_portal/1
population = {
    'Arlesheim': 157253,
    'Laufen': 20141,
    'Liestal': 61201,
    'Sissach': 36051,
    'Waldenburg': 16119,
}

# based on https://github.com/openZH/covid_19/issues/1185#issuecomment-709952315
initial_cases = {
    'Arlesheim': 528,
    'Laufen': 65,
    'Liestal': 177,
    'Sissach': 81,
    'Waldenburg': 15,
}

# order dict by key to ensure the most recent entry is last
ordered_rows = OrderedDict(sorted(rows.items()))

#for row_date, row in ordered_rows.items():
#    for district, district_id in district_ids.items():

for district, district_id in district_ids.items():
    last_total_cases_val = initial_cases[district]
    if district == 'Arlesheim':
        # 2020-05-31 is 527
        last_total_cases_val = 527

    for row_date, row in ordered_rows.items():
        dd = sc.DistrictData(canton='BL', district=district)
        dd.district_id = district_id
        dd.population = population[district]
        dd.url = main_url
        dd.date = row['date']
        dd.total_cases = row[district] + initial_cases[district]
        dd.new_cases = dd.total_cases - last_total_cases_val
        last_total_cases_val = dd.total_cases
        print(dd)
