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

url='http://www.npo.gov.za/PublicNpo'

page = requests.get(url)
page #<Response [200]> means we can webscrape site :-) - 404 means we can't

driver = webdriver.Chrome('C:/Users/f5463858/OneDrive - FRG/Dam_Level/chromedriver.exe')
driver.get(url) 

time.sleep(5)

clickthrough = driver.find_element(By.XPATH, '//*[@id="contentsec"]/div/div[1]/div[1]/h3[1]/a').click()
time.sleep(3) 

button1 = driver.find_element(By.XPATH, '//*[@id="Index-FilterButton"]').click()
time.sleep(1) 

input_box = driver.find_element(By.XPATH, '//*[@id="DateRegistered_GTE"]')
time.sleep(1) 
input_box.send_keys('01/01/2019')
time.sleep(1)

input_box1 = driver.find_element(By.XPATH, '//*[@id="DateRegistered_LTE"]')
time.sleep(1) 
input_box1.send_keys('31/12/2019')
time.sleep(1)

button2 = driver.find_element(By.XPATH, '//*[@id="Index-ApplyButton"]').click()
time.sleep(1)
button3 = driver.find_element(By.XPATH, '/html/body/div[4]/div[1]/a/span').click()

"""
#Part1:
"""  
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
#page_num_df=9000
#page_num_df=11000
check=0
count=0

while (page_num_df <= 2000):
#while (page_num_df <= 14044):
#while (page_num_df <= 13831):
    
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
        
        df.to_csv(r"C:\Users\f5463858\OneDrive - FRG\Desktop\_temp\NPOs\1997\\"+str(page_num_df)+".csv",index=False)
        
        check=0
    else:
        check+=1
    
    #if check >=80: #Keep checking if page updated.  If not updated force update
    if check >=40: #Keep checking if page updated.  If not updated force update
        next_page()
        check=1

# Close the Selenium webdriver
driver.close()








"""
Part2: Scrape NPO details
"""
os.chdir(r"C:\Users\f5463858\OneDrive - FRG\Desktop\_temp\NPOs")

#find all csv files in the folder
#use glob pattern matching -> extension = 'csv'
file_extension = 'csv'
#save result in list -> combined_files
combined_files = [i for i in glob.glob('*.{}'.format(file_extension))]
#print(combined_files)


#combine all files in the list
stacked_csv = pd.concat([pd.read_csv(j) for j in combined_files ])
#export to csv
stacked_csv.to_csv( "combined_output.csv", index=False, encoding='utf-8-sig')


# Load the data
df2 = pd.read_csv(r'NPO_output.csv', encoding= 'unicode_escape', low_memory=False)
# Check the dimension of data
print('Dimension of data: {} rows and {} columns'.format(len(df2), len(df2.columns)))
df2.rename(columns = {'ï»¿ID':'ID'}, inplace = True)
# Print the first 5 rows
df2.head()


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

"Start Here"

df3 

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

#pass in our dfs
df3,df_final= pre_pocessing(df3,df2)

df_final


df_final.to_csv(r"C:\Users\f5463858\OneDrive - FRG\Desktop\_temp\NPOs\combined_output_df_final_keanu.csv", index=False, encoding='utf-8-sig')