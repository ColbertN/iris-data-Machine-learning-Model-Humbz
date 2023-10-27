#print("Loading in Libs")
import json
import urllib.parse
import boto3
import pandas as pd
from io import BytesIO
import io

#Webstuff
from bs4 import BeautifulSoup
import requests, os, urllib.parse, urllib3, time, random
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import string
import re
urllib3.disable_warnings()
import numpy as np

#print('Functions_loaded')

#########################################################
def save_to_s3(df_save,bucket_save,csv_name):
    with io.StringIO() as csv_buffer:
        df_save.to_csv(csv_buffer, index=False)

        response = s3.put_object(
            Bucket=bucket_save, Key=csv_name, Body=csv_buffer.getvalue()
        )
    
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    
        if status == 200:
            print(f"Successful S3 put_object response. Status - {status}")
        else:
            print(f"Unsuccessful S3 put_object response. Status - {status}")
            
###########################################################  


#Webscraping stuff
retry_strategy = Retry(
    total=5,
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
        time.sleep(1)
        #time.sleep(random.uniform(0.2,0.7))
        return None
    else:
        #print(f"Proxy -> {proxies[proxy_select].get('http','')}{proxies[proxy_select].get('https','')}")
        return proxies[proxy_select]

def get_user_agents():
    userAgents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.193 Safari/537.36 Edg/86.0.622.63"
        ]

    return userAgents

def rotate_user_agent(userAgents):
    return userAgents[random.randint(0,len(userAgents)-1)]



def buildSearchUrl(queryInput):
    return f"https://google.co.za/search?q=" + "+".join(queryInput.split()) + "&cr=countryZA"



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
        div = soup.find("div", class_="SPZz6b")
        name = None
        if div:
            for tag in div:
                if tag.attrs.get("data-attrid") == 'title':
                    name = tag.string
                    break
                else:
                    name = None
        else: name = None

        industry = soup.find("span", class_='YhemCb')
        if industry: industry = industry.text
        else: industry = None
            
        '''enter other code attributes here'''
        rating = soup.find("span", class_='z3HNkc')
        if rating: rating = rating["aria-label"][:18]
        else: rating = None
        
        
        no_of_review = soup.find("span", class_='hqzQac')
        if no_of_review: no_of_review = no_of_review.text.split("\n")[0]
        else: no_of_review = None

        if name or industry or no_of_review or rating:
            return {"name":name, "industry":industry, "Rating":rating, "no_of_review":no_of_review}
        else:
            return None


#Web end

print("s3 setup")            
s3_save_bucket_name="edabusinessindustrysavedoutputs"
s3 = boto3.client('s3')

print("go to lamb")
def lambda_handler(event, context):
    #print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    try:
        time.sleep(2)
        response = s3.get_object(Bucket=bucket, Key=key)
        print("Key",key)
        print("bucker:",bucket)
        print("CONTENT TYPE: " + response['ContentType'])
        
        #if response['ContentType']=="text/csv":
        if (1+1)==2:
            print("CSV file loaded")
            df_s3_data = pd.read_csv(response['Body'], sep=',')
            name=df_s3_data.iloc[0,df_s3_data.columns.get_loc("CUST_NAME")]
            row_num=df_s3_data.iloc[0,df_s3_data.columns.get_loc("ROW")]
            #name="civils 2000"
            print("Name:",name)
            #print("ROW",row_num)
            
            #Enter code for webscraping
            
            outcome = parse_listing(buildSearchUrl(name), get_proxies())
            print(outcome)
            print("done outcome")
            if outcome is not None and outcome.get("name", 0) !=0 and outcome.get("industry", 0) !=0:
                print("in outcome")
                google_name=outcome.get("name", 0)
                google_indus=outcome.get("industry", 0)
                google_rating=outcome.get("Rating", 0)
                google_no_of_reviews=outcome.get("no_of_review", 0)
                #print("Here1")
                df = pd.DataFrame(
                    data={"Our_Name": [name], "G_name": [google_name],"G_indus":[google_indus],"G_ratings": [google_rating],"G_reviews": [google_no_of_reviews],"ROW":[row_num]},
                    columns=["Our_Name", "G_name","G_indus","G_ratings","G_reviews","ROW"],index=None)
                #Save output
                print("saving")
                save_to_s3(df,s3_save_bucket_name,str(row_num)+".csv")
                #save_to_s3(df,s3_save_bucket_name,name+".csv")
                print("saving worked")
            else:
                print("Done failed")
                pass
                # print("here3")
                # df = pd.DataFrame(
                #     data={"Our_Name": [name]},
                #     columns=["Our_Name"],index=None)
                # save_to_s3(df,s3_save_bucket_name,"Failed/"+name+".csv")
                
            
            #print(df_s3_data.head())
        
        
        return response['ContentType']
    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        raise e
