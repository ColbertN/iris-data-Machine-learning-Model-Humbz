#lambda can only run for 15min

from datetime import datetime
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re,os,glob,time,string
import requests
import web_general
import subprocess
import boto3
import io

print("s3 setup")
s3_save_bucket_name="fnb-commercial-npodata"
s3 = boto3.client('s3')

print("chrome options")
options = Options()
options.binary_location = os.getcwd() + '/opt/headless-chromium'

print("arguments")
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")


print('version')
print(webdriver.Chrome(service=Service('/opt/chromedriver')).capabilities['browserVersion'])

print("driver")
driver = webdriver.Chrome(chrome_options=options)

print("save function")
def save_to_s3(df_save,bucket_save,csv_name):
    with io.StringIO() as csv_buffer:
        df_save.to_csv(csv_buffer, index=False)
        response = s3.put_object(Bucket=bucket_save, Key=csv_name, Body=csv_buffer.getvalue())
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status == 200:
            print(f"Successful S3 put_object response. Status - {status}")
        else:
            print(f"Unsuccessful S3 put_object response. Status - {status}")

run_date = (datetime.now().date() - relativedelta(months=1)).replace(day=1).strftime('%d/%m/%Y')
print(run_date)
print("declaring url")
url='http://www.npo.gov.za/PublicNpo'
print("page")
page = requests.get(url)
page #<Response [200]> means we can webscrape site :-) - 404 means we can't


print("get url")
driver.get(url)
time.sleep(5)

print("Navigating page")
clickthrough = driver.find_element(By.XPATH, '//*[@id="contentsec"]/div/div[1]/div[1]/h3[1]/a').click()
time.sleep(3) 

button1 = driver.find_element(By.XPATH, '//*[@id="Index-FilterButton"]').click()
time.sleep(1) 

input_box = driver.find_element(By.XPATH, '//*[@id="DateRegistered_GTE"]')
time.sleep(1) 

input_box.send_keys('01/04/2023')
#input_box.send_keys(run_date)
time.sleep(1)

button2 = driver.find_element(By.XPATH, '//*[@id="Index-ApplyButton"]').click()
time.sleep(1)
button3 = driver.find_element(By.XPATH, '/html/body/div[4]/div[1]/a/span').click()

"""
#Part1:
"""  
print("part 1 start")
def next_page():
    button = driver.find_element(By.ID, "next_PublicNpoSearch_Index-Pager")
    button.click()

def get_details_save(rows_,count,df):
    for row in rows_[1:]:
        hold_list=[]
        for item in row:
            hold_list.append(item.text)
        hold_list.append(count)
        df.loc[len(df)] = hold_list
    return df

def get_rows(driver):
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    table=soup.find(lambda tag: tag.name=='table' and tag.has_attr('id') and tag['id']=="PublicNpoSearch_Index-Table") 
    rows = table.findAll(lambda tag: tag.name=='tr')
    page_view=soup.find("div", class_="scroll ui-state-default ui-jqgrid-pager ui-corner-bottom").text
    return rows,page_view

def get_details(rows_,count):
    for row in rows_[1:]:
        hold_list=[]
        for item in row:
            hold_list.append(item.text)
        hold_list.append(count)
        save_list=hold_list
        last_name=hold_list[4]
    return save_list, last_name

page_num_df=0
check=0
count=0

while (page_num_df <= 5): #dinamically get max pages
    
    #First time it comes here it goes to next page
    if check==0:
        next_page()
        
    rows,page_view=get_rows(driver)
    page_view=int(int(page_view.split("-")[1].split("of")[0].replace(" ", ""))/20)
    
    if page_num_df!=page_view:
        df = pd.DataFrame(columns=["ID","Search","Name","Province","Reg_no","DOR","Status","DC","FM","Page"])
        save_list, last_name=get_details(rows,count)
        df=get_details_save(rows,page_view,df)
        page_num_df=df.iloc[-1,df.columns.get_loc("Page")]
        print(page_num_df,end="\r")
        page_num_df=page_view
        
        save_to_s3(df,s3_save_bucket_name,str(page_num_df)+".csv")
        
        check=0
    else:
        check+=1
    
    if check >=40: #Keep checking if page updated.  If not updated force update
        next_page()
        check=1

# Close the Selenium webdriver
driver.close()

"""
Part2:
"""
# Define file extension
file_extension = '.csv'
# Get list of all files with the specified extension
s3 = boto3.resource('s3')
bucket = s3.Bucket(s3_save_bucket_name)
files = bucket.objects.all()
file_list = [s3_object.key for s3_object in files if s3_object.key.endswith(file_extension)]

# Concatenate all CSV files into one DataFrame
dfs = [pd.read_csv(f's3://{s3_save_bucket_name}/{file}') for file in file_list]
combined_df = pd.concat(dfs, ignore_index=True)
#saving the final output
save_to_s3(combined_df,s3_save_bucket_name,"combined_output.csv")

# Read the CSV file from S3
csv_name = 'combined_output.csv'
response = s3.get_object(Bucket=s3_save_bucket_name, Key=csv_name)
body = response['Body'].read().decode('utf-8')
df = pd.read_csv(io.StringIO(body))

# Check the dimension of data
print('Dimension of data: {} rows and {} columns'.format(len(df2), len(df2.columns)))
df2.rename(columns = {'ï»¿ID':'ID'}, inplace = True)

id_list = df2['ID'].astype(str).values.tolist()

URL='https://www.npo.gov.za/PublicNpo/Npo'

soup=web_general.parse_listing(web_general.buildSearchUrl(URL), web_general.get_proxies())
if not soup:print("Not found")
else: print("good to go")

base_url="https://www.npo.gov.za/PublicNpo/Npo/DetailsPublicDocs/"

# creating empty list
name_list = []
reg_no_list = []
cat123_list = []
NPOType_list = []
dor_list = []

for ID in id_list:
    search_url=base_url+ID
    soup=web_general.parse_listing(web_general.buildSearchUrl(search_url), web_general.get_proxies())
    #passing through all web scrapped files to a list
    name_list.append(soup.find("h1", class_="widget-head-border colr").text.split("\n")[1])
    reg_no_list.append(soup.find("div", class_="padbox").text.split("\n")[7])
    cat123_list.append(soup.find("div", class_="padbox").text.split("\n")[8])
    NPOType_list.append(soup.find("div", class_="padbox").text.split("\n")[10])
    dor_list.append(soup.find("div", class_="padbox").text.split("\n")[13])
    
# create df and pass in all lists created above
pd.set_option('display.max_colwidth', None)
df3 = pd.DataFrame(np.column_stack([id_list, name_list, reg_no_list, cat123_list, NPOType_list, dor_list ]),
                  columns=["ID","Name","Reg_no","Cat123","NPO_Type","DOR"])

def pre_pocessing(df3,df4):
    #spliting 
    df3[["cat1", "cat2", "cat3"]] = df3['Cat123'].str.split(pat='>',expand=True)
    #removing all uncessary words in each column
    df3['cat3'] = df3['cat3'].str.replace("\r", "", regex=True)
    df3.drop(["Cat123"], axis=1, inplace= True)
    df3['DOR'] = df3['DOR'].str.replace("\r", "", regex=True)
    df3['Name'] = df3['Name'].str.replace("NPO Details:", "", regex=True)
    df3['Reg_no'] = df3['Reg_no'].str.replace("Registration No.:", "", regex=True)
    # Remove all the leading spaces
    for column in ['ID', 'Name', 'Reg_no', "cat1", "cat2", "cat3", 'NPO_Type', 'DOR']:
        df3[column] = df3[column].astype(str)
        df3[column] = df3[column].apply(lambda x:x.strip().replace(r'\s+',' '))
    df3["ID"] = df3["ID"].astype(int)
    df_final = df3.merge(df4, on= ['ID', 'Reg_no', 'DOR'], how='left')
    return df3,df_final

#pass in our dfs into 
df3,df_final= pre_pocessing(df3,df2)

save_to_s3(df_final,s3_save_bucket_name,"combined_output_df_final.csv")