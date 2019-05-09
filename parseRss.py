import feedparser
from bs4 import BeautifulSoup
import urllib
import xmltodict
import pandas as pd
import re
import os
import datetime

# build list of links to parse from:
def build_company_list():
    startnum = 0
    entryamt = 100
    url = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=13f-hr&company=&dateb=&owner=include&start={}&count={}&output=atom'.format(
        startnum, entryamt)
    d = feedparser.parse(url)
    entrylist = d['entries']
    entries = d['entries']

    while len(entries) == 100:
        url = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=13f-hr&company=&dateb=&owner=include&start={}&count={}&output=atom'.format(
            startnum, entryamt)
        d = feedparser.parse(url)
        entries = d['entries']
        entrylist = entrylist + d['entries']
        startnum += 100
    return entrylist


def parse_link(entrylist, list_index):
    url = entrylist[list_index]['link']
    print(list_index, url)
    page = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(page, 'html.parser')

    # get company name and CIK
    companyname = soup.find('span', class_='companyName').contents[0]
    companyname = re.sub(' \(Filer\) ', '', companyname)
    contents = soup.find('span', class_='companyName').contents[3]
    companyCIK = re.sub('<.*?>', '', str(contents))
    companyCIK = re.sub(' \(.*?\)', '', companyCIK)

    # find report date and filing date
    links = soup.find_all('div', class_='formGrouping')
    filingDate = links[0].find_all('div', class_='info')[0].contents[0]
    reportDate = links[1].find_all('div', class_='info')[0].contents[0]

    # find the securities
    for link in soup.find_all('a'):
        securities_url = link.get('href')
        text = link.contents[0]
        if '.xml' in securities_url and 'xml' in text and 'primary_doc' not in securities_url:
            securities_list = securities_url

    # build proper url
    securities_list_url = 'https://www.sec.gov{}'.format(securities_list)
    data = urllib.request.urlopen(securities_list_url).read()
    namespaces = {'http://www.sec.gov/edgar/document/thirteenf/informationtable': None}
    securities = xmltodict.parse(data, process_namespaces=True, namespaces=namespaces)
    securities_list = securities['informationTable']['infoTable']

    if isinstance(securities_list, list):
        df = pd.DataFrame.from_dict(securities_list)
    else:
        df = pd.DataFrame.from_dict(securities_list, orient='index').transpose()

    if 'putCall' not in df.columns:
        df.insert(5, 'putCall', '')
    if 'otherManager' not in df.columns:
        df.insert(7, 'otherManager', '')

    df['sshPrnamt'] = [d.get('sshPrnamt') for d in df.shrsOrPrnAmt]
    df['sshPrnamtType'] = [d.get('sshPrnamtType') for d in df.shrsOrPrnAmt]
    df['votingSole'] = [d.get('Sole') for d in df.votingAuthority]
    df['votingShared'] = [d.get('Shared') for d in df.votingAuthority]
    df['votingNone'] = [d.get('Shared') for d in df.votingAuthority]
    df['companyName'] = companyname
    df['companyCIK'] = companyCIK
    df['reportDate'] = reportDate
    df['filingDate'] = filingDate
    df.replace(r'\s+|\\n', ' ', regex=True, inplace=True)
    return df


# go through each and every company item and then dump into csv file
def write_to_file(clist, filename):
    for i in range(len(clist)):
        df = parse_link(clist, i)
        df.drop(columns=['shrsOrPrnAmt', 'votingAuthority'], inplace=True)

        if os.path.isfile(filename):
            pass
        else:
            pd.DataFrame(df.columns).transpose().to_csv(filename, header=False, index=False, mode='a', sep='^')

        df.to_csv(filename, header=False, index=False, mode='a', sep='^')


time_now = datetime.datetime.now().strftime('%Y%m%d')
companylist = build_company_list()
write_to_file(companylist, '{}.csv'.format(time_now))

