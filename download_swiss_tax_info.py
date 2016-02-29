#! /usr/bin/env python

import StringIO
import csv
import simplejson
import sys
import urllib2

import BeautifulSoup


ICTAX_JSON = 'https://www.ictax.admin.ch/extern/api/instrument/instrument.json'
ICTAX_REF_DATES = {
    2011: 1325289600000,
    2012: 1356912000000,
    2013: 1388448000000,
    2014: 1419984000000,
    2015: 1451520000000,
}
ALL_SWISS_STOCKS_CSV = (
        'http://www.six-swiss-exchange.com/shares/companies/download/'
        'issuers_all_de.csv')


def download_swiss_stocks():
    response = urllib2.urlopen(ALL_SWISS_STOCKS_CSV)
    reader = csv.reader(response, delimiter=';')
    reader.next()  # Skip header row.
    stocks = []
    for row in reader:
        stocks.append((row[0].strip(), row[2].strip()))
    return stocks


def download_tax_info(valor_number, year):
    request = {
        'valorNumber': valor_number,
        'isin': None,
        'referenceDate': ICTAX_REF_DATES[year],
        'language': 'de',
    }
    data_json = simplejson.dumps(request)
    req = urllib2.Request(
            ICTAX_JSON,
            data_json,
            {'Content-Type': 'application/json'})
    response = urllib2.urlopen(req)
    return simplejson.loads(response.read())


def parse_tax_info(name, html):
    soup = BeautifulSoup.BeautifulSoup(html)
    rows = soup.find('tbody').findAll('tr')
    value = 0
    kep = 0
    dividends = 0
    for row in rows:
        cells = row.findAll('td')
        if len(cells) != 13:
            print >>sys.stderr, 'Unexpected number of columns for %s: %d' % (
                    name, len(cells))
            continue
        value += parse_number(cells[4].getText())
        kep += parse_number(cells[10].getText())
        dividends += parse_number(cells[11].getText())
    return value, kep, dividends


def download_swiss_stocks_and_tax_info():
    stocks = []
    for name, valor_number in download_swiss_stocks():
        cols = [name, valor_number]
        for year in ICTAX_REF_DATES.keys():
            tax_info = download_tax_info(valor_number, year)
            if tax_info['status'] == 'SUCCESS':
                html = tax_info['data']['html']
                value, kep, dividends = parse_tax_info(name, html)
            else:
                print >>sys.stderr, 'Failed to get tax info for %s in %d' % (
                        name, year)
                value, kep, dividends = 0.0, 0.0, 0.0
            cols += [value, kep, dividends]
        print cols
        stocks.append(cols)
    return stocks


def main(argv=None):
    stocks = download_swiss_stocks_and_tax_info()

    # Header.
    header = ['Name', 'Valor']
    for year in ICTAX_REF_DATES.keys():
        header += ['Value %d' % year, 'KEP %d' % year, 'Dividends %d' % year]

    string_io = StringIO.StringIO()
    writer = csv.writer(string_io)
    writer.writerows([header] + stocks)
    print string_io.getvalue()
    string_io.close()


def parse_number(string):
    try:
        return float(string.replace('&nbsp;', '').replace('&#160;', ''))
    except ValueError, e:
        return 0.0


if __name__ == '__main__':
    sys.exit(main())
