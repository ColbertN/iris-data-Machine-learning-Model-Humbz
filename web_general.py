
from bs4 import BeautifulSoup
import requests, os, csv, urllib.parse, urllib3, time, random
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import numpy as np
import pandas as pd

import string
import time
import re
urllib3.disable_warnings()

import os
import glob

retry_strategy = Retry(
    total=20,
    status_forcelist=[429, 500, 502, 503, 504],
    method_whitelist=["HEAD", "GET", "OPTIONS"],
    backoff_factor=2
)

adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)

def get_proxies():
    proxyList = [
        {"http":"169.159.179.248:8080"}, {"http":"105.208.17.58:8080"}, {"http":"160.119.44.210:8080"}, {"http":"196.214.145.106:80"},
        {"https":"41.194.37.106:45381"},{"https":"41.222.159.191:8080"},{"https":"66.251.179.207:8080"}
        ]
    return proxyList

def rotate_proxy(proxies):
    proxy_select = -1
    if int(os.getenv('proxy_enabled', default=0)) > 0:
        proxy_select = random.randint(-1,len(proxies)-1)
    if proxy_select < 0:
        time.sleep(random.uniform(0.2,0.5))
        return None
    else:
        print(f"Proxy -> {proxies[proxy_select].get('http','')}{proxies[proxy_select].get('https','')}")
        return proxies[proxy_select]

def get_user_agents():
    userAgents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.193 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv: 82.0) Gecko/20100101 Firefox/82.0",
        "Mozilla/5.0 (Windows NT 10.0; Trident/7.0; rv:11.0) like Gecko",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.193 Safari/537.36 Edg/86.0.622.63"
        ]
    return userAgents

def rotate_user_agent(userAgents):
    return userAgents[random.randint(0,len(userAgents)-1)]

def buildSearchUrl(queryInput):
    return queryInput


def makeRequest(url, header,proxy):
    return http.get(url, headers=header, proxies=proxy, verify=False)


def parse_listing(url, proxies):
    proxy = rotate_proxy(proxies)
    user_agent = rotate_user_agent(get_user_agents())
    headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
               'Accept-Language': 'en-US,en;q=0.9,af;q=0.8',
               'Accept-Encoding': 'gzip, deflate, br',
               'Connection': 'keep-alive',
               'Upgrade-Insecure-Requests': '1',
               'User-Agent': user_agent}
    try:
        req = makeRequest(url, headers, proxy)
    except:
        return None

    if req:
        soup = BeautifulSoup(req.content, 'lxml')
    else:
        return None
    if not soup:
        return None
    else:
        return soup
