import requests
from bs4 import BeautifulSoup
import numpy as np
import urllib.request, json , os, difflib, itertools
import pandas as pd
from multiprocessing.dummy import Pool
from datetime import datetime

query_url="https://query1.finance.yahoo.com/v8/finance/chart/AAPL?symbol=AAPL"

try:
    with urllib.request.urlopen(query_url) as url:
        parsed = json.loads(url.read().decode())
except:
    pass


parsed

print("Stock price for Apple is: ",parsed['chart']['result'][0]['meta']['regularMarketPrice'])
def get_historic_price(query_url,csv_path):
    
    stock_id=query_url.split("&period")[0].split("symbol=")[1]
    
    if os.path.exists(csv_path+stock_id+'.csv') and os.stat(csv_path+stock_id+'.csv').st_size != 0:
        print("<<<  Historical data of "+stock_id+" already exists, Updating data...")

    try:
        with urllib.request.urlopen(query_url) as url:
            parsed = json.loads(url.read().decode())
    except:
        print("|||  Historical data of "+stock_id+" doesn't exist")
        return
    
    else:

        try:
            Date=[]
            for i in parsed['chart']['result'][0]['timestamp']:
                Date.append(datetime.utcfromtimestamp(int(i)).strftime('%d-%m-%Y'))
                
            Low=parsed['chart']['result'][0]['indicators']['quote'][0]['low']
            Open=parsed['chart']['result'][0]['indicators']['quote'][0]['open']
            Volume=parsed['chart']['result'][0]['indicators']['quote'][0]['volume']
            High=parsed['chart']['result'][0]['indicators']['quote'][0]['high']
            Close=parsed['chart']['result'][0]['indicators']['quote'][0]['close']
            Adjusted_Close=parsed['chart']['result'][0]['indicators']['adjclose'][0]['adjclose']

            df=pd.DataFrame(list(zip(Date,Low,Open,Volume,High,Close,Adjusted_Close)),columns =['Date','Low','Open','Volume','High','Close','Adjusted Close'])

            if os.path.exists(csv_path+stock_id+'.csv'):
                os.remove(csv_path+stock_id+'.csv')
            df.to_csv(csv_path+stock_id+'.csv', sep=',', index=None)
            print(">>>  Historical data of "+stock_id+" saved")
            return
        except:
            print(">>>  Historical data of "+stock_id+" exists but has no trading data")


query_url1="https://query1.finance.yahoo.com/v8/finance/chart/GOOGL?symbol=GOOGL&period1=0&period2=9999999999&interval=1d&includePrePost=true&events=div%2Csplit" 
csv_path1 = os.getcwd()+os.sep+"all_historic_data_Google"+os.sep+"csv"+os.sep

## Create directory if not already present
if not os.path.isdir(csv_path1):
    os.makedirs(csv_path1)
get_historic_price(query_url1, csv_path1) 

query_url2="https://query1.finance.yahoo.com/v8/finance/chart/META?symbol=META&period1=1640995200&period2=1643587200&interval=1d&includePrePost=true&events=div%2Csplit"
csv_path2 = os.getcwd()+os.sep+"nov2024_data_Meta"+os.sep+"csv"+os.sep

## Create directory if not already present
if not os.path.isdir(csv_path2):
    os.makedirs(csv_path2)
get_historic_price(query_url2, csv_path2) 

df_meta = pd.read_csv(csv_path2+"META.csv")
df_meta.head()

ticker_file_path = "Yahoo Tickers.xlsx"
temp_df = pd.read_excel(ticker_file_path)
print("Total stocks:",len(temp_df))
temp_df.head(10)

temp_df = temp_df.drop(temp_df.columns[[5, 6, 7]], axis=1)
headers = temp_df.iloc[2]
df  = pd.DataFrame(temp_df.values[3:], columns=headers)
print("Total stocks:",len(df))
df.head(10)

df_subset = df.sample(1000)

df_subset.Country.unique()

df_subset.dropna(subset=['Country'],inplace=True)
df_subset.shape

ticker_list = df_subset['Name'].tolist()
query_urls=[]
for ticker in ticker_list:
    query_urls.append("https://query1.finance.yahoo.com/v8/finance/chart/"+ticker+"?symbol="+ticker+"&period1=1359657000&period2=1361989800&interval=1d&includePrePost=true&events=div%2Csplit")
    
csv_path3 = os.getcwd()+os.sep+"historic_data_2013"+os.sep+"csv"+os.sep

## Create directory if not already present
if not os.path.isdir(csv_path3):
    os.makedirs(csv_path3)
    
with Pool(processes=len(query_urls)) as pool:
    pool.starmap(get_historic_price, zip(query_urls, itertools.repeat(csv_path3)))
print("All downloads completed !")

    