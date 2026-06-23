import requests as rq
import pandas as pd
from config import POLYGON_API_KEY,DATA_BASE_URL


SUFFIX = f'&adjusted=true&sort=asc&limit=50000&apiKey={POLYGON_API_KEY}'

def fetch(url):
    res = rq.get(url)
    
    if res.status_code != 200:
        raise Exception(f"Failed to fetch data from {url}")
      
    return res.json()


def get_ticker(ticker, start, end):
    url = f'{DATA_BASE_URL}/{ticker}/range/1/minute/{start}/{end}?{SUFFIX}'
    res = fetch(url)
    
    data = res['results']
    count = 1
    
    while('next_url' in res):
        res = fetch(f"{res['next_url']}{SUFFIX}")
        data.extend(res['results'])
        count+=1
    
    df = pd.DataFrame(data)
    df.rename(columns={
                      't': 'Datetime',
                      'o': 'Open',
                      'h': 'High',
                      'l': 'Low',
                      'c': 'Close',
                      'v': 'Volume',
                      'n': 'Trade Count',
                      'vw': 'VWAP'
              }, 
              inplace=True
            )
    
    df["Datetime"] = pd.to_datetime(df['Datetime'], unit='ms')
    df['Datetime'] = df['Datetime'].dt.tz_localize('UTC')
    df.set_index('Datetime', inplace=True)
    print(df.head())
    
    return df