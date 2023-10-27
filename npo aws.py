"""
import json
import os
import shutil
import uuid
import boto3
from datetime import datetime
import datetime
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os, csv, urllib.parse, urllib3, random
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
urllib3.disable_warnings()


from selenium import webdriver
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
#from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re
import glob 
import time 
import string
import requests
import web_general
import subprocess
import boto3
import io



class WebDriver(object):

    def __init__(self):
        self.options = Options()

        self.options.binary_location = '/opt/headless-chromium'
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--start-maximized')
        self.options.add_argument('--start-fullscreen')
        self.options.add_argument('--single-process')
        self.options.add_argument('--disable-dev-shm-usage')
       # self.options.add_argument(f'--proxy-server="http://proxyo.fnb.co.za"')
    def get(self):
        driver = Chrome('/opt/chromedriver', options=self.options)
        return driver



 
def save_df_to_s3(df, csv_name):
     csv_buffer= io.StringIO()
     df.to_csv(csv_buffer, index=False)
     csv_data = csv_buffer.getvalue()
     
     s3 = boto3.client('s3')
     s3_save_bucket_name="fnb-commercial-npodata"
     
     s3.put_object(Body= csv_data, Bucket= s3_save_bucket_name, Key=csv_name)





def lambda_handler(event, context):
    
    instance_ = WebDriver()
    driver = instance_.get()
    driver.get('http://www.npo.gov.za/PublicNpo')
    time.sleep(5)
    
    print(driver.page_source)
     
    run_date = (datetime.now().date() - relativedelta(months=1)).replace(day=1).strftime('%d/%m/%Y')
    print(run_date)
    print("declaring url")
    url="http://www.npo.gov.za/PublicNpo"
    #print("page")
   
    #page = requests.get(url)
    #page #<Response [200]> means we can webscrape site :-) - 404 means we can't

    
   
    
    print("Navigating page")
    clickthrough = driver.find_element(By.XPATH, '//*[@id="contentsec"]/div/div[1]/div[1]/h3[1]/a').click()
    time.sleep(3) 
    
    button1 = driver.find_element(By.XPATH, '//*[@id="Index-FilterButton"]').click()
    time.sleep(1) 
    
    input_box = driver.find_element(By.XPATH, '//*[@id="DateRegistered_GTE"]')
    time.sleep(1) 
    
    input_box.send_keys('04/07/2023')
    #input_box.send_keys(run_date)
    time.sleep(1)
    
    button2 = driver.find_element(By.XPATH, '//*[@id="Index-ApplyButton"]').click()
    time.sleep(1)
    button3 = driver.find_element(By.XPATH, '/html/body/div[4]/div[1]/a/span').click()
    
    
    #Part1:
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
    
    while (page_num_df <= 6): #dinamically get max pages
        
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
            
            
            save_df_to_s3(df, str(page_num_df)+".csv")
            #print(df.head(1))
            
            check=0
        else:
            check+=1
        
        if check >=40: #Keep checking if page updated.  If not updated force update
            next_page()
            check=1
    
    # Close the Selenium webdriver
    driver.close()


    #Part2:
    

    # Define file extension
    file_extension = '.csv'
    # Get list of all files with the specified extension
    s3 = boto3.resource('s3')
    s3_save_bucket_name="fnb-commercial-npodata"
    bucket = s3.Bucket(s3_save_bucket_name)
    files = bucket.objects.all()
    file_list = [s3_object.key for s3_object in files if s3_object.key.endswith(file_extension)]
    
    # Concatenate all CSV files into one DataFrame
    dfs = [pd.read_csv(f's3://{s3_save_bucket_name}/{file}') for file in file_list]
    combined_df = pd.concat(dfs, ignore_index=True)
    

    s3 = boto3.client('s3')
    #combined_df= pd.DataFrame()
    
    bucket_name= "fnb-commercial-npodata"
    
    
    response = s3.list_objects(Bucket=bucket_name)
    
    for obj in response['Contents']:
        
        file_key= obj['Key']
        
        if file_key.endswith(".csv"):
            obj_data=s3.get_object(Bucket=bucket_name, Key=file_key)
            df_1= pd.read_csv(obj_data['Body'])
            
            combined_df= pd.concat([combined_df,df_1])
            
    
    print(combined_df.head())
    
    save_df_to_s3(combined_df, "combined_output.csv")

   
    bucket_name= "fnb-commercial-npodata"

    
    
    

    # Read the CSV file from S3
    csv_name = 'combined_output.csv'
    response = s3.get_object(Bucket=bucket_name, Key=csv_name)
    body = response['Body'].read().decode('utf-8')
    df2 = pd.read_csv(io.StringIO(body))
    
    # Check the dimension of data
    print('Dimension of data: {} rows and {} columns'.format(len(df2), len(df2.columns)))
    df2.rename(columns = {'ï»¿ID':'ID'}, inplace = True)
    
    
    id_list = df2['ID'].astype(str).values.tolist()
    
    URL='https://www.npo.gov.za/PublicNpo/Npo'
    
    soup= parse_listing(buildSearchUrl(URL), get_proxies())
    
    
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
        soup=parse_listing(buildSearchUrl(search_url), get_proxies())
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
    
   # save_to_s3(df_final,s3_save_bucket_name,"combined_output_df_final.csv")
    
    save_df_to_s3(df_final, "combined_output_df_final.csv")
 

    return True
    """
    

# import requests
import os
import glob
import sys

# def get_python_directory():
#     # Get the path of the Python executable
#     python_path = sys.executable
#     # Get the directory name of the Python executable
#     python_dir = os.path.dirname("botocore")
#     # Print the Python directory
#     print(python_dir)


# def list_directories(thing):
#     # Get the list of directories in the root directory
#     dirs = [d for d in os.listdir(thing) if os.path.isdir(os.path.join('/', d))]
#     # Print each directory name
#     for d in dirs:
#         print(d)

def find_file(file_name):
    # Start from the root directory
    root_dir = '/'
    # Walk through the directory tree
    for dir_path, dir_names, file_names in os.walk(root_dir):
        # Check if the file name is in the current directory
        if file_name in file_names:
            # Print the full path of the file
            file_path = os.path.join(dir_path, file_name)
            print(file_path)
            # Break the loop
            break
    else:
        # If the loop finishes without finding the file, print a message
        print('File not found')
        

        
# thing = "/var/lang/bin/"       
print("10")
# list_directories(thing)
find_file("cacert.pem")
print("11")
# get_python_directory()
# def list_files(directory):
#     # Get the list of files in the given directory
#     files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
#     # Print each file name
#     for f in files:
#         print(f)
        
# list_files("/var/lang/lib/python*/")


catcert_path="/var/runtime/botocore/cacert.pem"
frg_cert_path="/opt/frg_bundled"
# os.environ["http_proxy"] = "https://proxyo.fnb.co.za"
# os.environ["https_proxy"] = "https://proxyo.fnb.co.za"

def lambda_handler(event, context):
  
  ###Certs
  print("1")
  print(os.listdir('/tmp/'))
  print("2")
  print(f"Event received: {event}")
  certfile = 'not_found'
  for certfile in glob.glob(catcert_path):
      print(f'included certs {certfile}')
  pem = ''
  with open(certfile, 'r') as pemfile:
      pem += pemfile.read()
  for f in os.listdir(frg_cert_path):
      # print(f"Pemfile:{f}")
      with open(f'{frg_cert_path}/{f}', 'r') as frgpemfile:
          pem += frgpemfile.read()
  # print(f'Final CA certs contents:\n{pem}')
  with open('/tmp/cacerts.pem', 'w') as full_pem:
      full_pem.write(pem)
  print("3")
  print(os.listdir('/tmp/'))

  ###Certs end
  
#   # Get the URL to connect to
#   url = "https://google.com"

#   # Try to connect to the URL
#   try:
#     response = requests.get(url)
#   except Exception as e:
#     # If the connection fails, log the error and return
#     print(e)
#     return

#   # If the connection succeeds, return the response
#   return response.content

  import requests
  
  url = "http://www.geeksforgeeks.org"
  
  try:
    print("4")
    response = requests.get(url)
    
    print("6")
  
    print("Status code:", response.status_code)
  
    print("7")
    
    print("Content:", response.text)
    
  except Exception as e:
    print ("5")
    print(e)
  