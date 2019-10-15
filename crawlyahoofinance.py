# -*- coding: utf-8 -*-
"""crawlYahooFinance.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Bjk7gNKsjcjHPzMZQmqQhi5L38iBMmTj
"""

import bs4 as bs
import urllib.request
import pandas as pd
from time import sleep
from lxml import html  
import requests
from time import sleep
import json
import argparse
from collections import OrderedDict
import lxml.html as lh
import pandas as pd

def getSummaryData(url):
  response = requests.get(url, verify=False)
  print ("Parsing %s"%(url))
  sleep(4)
  parser = html.fromstring(response.text)
  summary_table = parser.xpath('//div[contains(@data-test,"summary-table")]//tr')
  summary_data = OrderedDict()
  try:
    for table_data in summary_table:
      raw_table_key = table_data.xpath('.//td[contains(@class,"C($primaryColor)")]//text()')
      raw_table_value = table_data.xpath('.//td[contains(@class,"Ta(end)")]//text()')
      table_key = ''.join(raw_table_key).strip()
      table_value = ''.join(raw_table_value).strip()
      summary_data.update({table_key:table_value})
    return summary_data
  
  except:
    print ("Failed to parse json response")
    return {"error":"Failed to parse json response"}

def getFinanceData(url):
  response = requests.get(url, verify=False)
  print ("Parsing %s"%(url))
  sleep(4)
  parser = html.fromstring(response.text)
  summary_table = parser.xpath('//div[contains(@data-test,"fin-row")]')
  print(len(summary_table))
  summary_data = pd.DataFrame()

  for table_data in summary_table:
    raw_table_key = table_data.xpath('.//span[contains(@class,"Va(m)")]//text()')

    raw_table_value = table_data.xpath('.//span[not(contains(@class,"Va(m)"))]//text()')

    print('table_key', raw_table_key)
    print('table_value', raw_table_value)
    
  return summary_data
    
# empty cells, heirarchical cells

financeUrl = "https://finance.yahoo.com/quote/TSLA/financials?p=TSLA"
scrappedData = getFinanceData(financeUrl)
print(scrappedData)

def parse_url(url):
  response = requests.get(url)
  soup = bs.BeautifulSoup(response.text, 'lxml')
  
  listdf = []
  
  for table in soup.find_all('table'):
    listdf.append(parse_html_table(table))
  
  return listdf
    
def parse_html_table(table):
  n_columns = 0
  n_rows=0
  column_names = []

  # Find number of rows and columns
  # we also find the column titles if we can
  for row in table.find_all('tr'):

      # Determine the number of rows in the table
      td_tags = row.find_all('td')
      if len(td_tags) > 0:
          n_rows+=1
          if n_columns == 0:
              # Set the number of columns for our table
              n_columns = len(td_tags)

      # Handle column names if we find them
      th_tags = row.find_all('th') 
      if len(th_tags) > 0 and len(column_names) == 0:
          for th in th_tags:
              column_names.append(th.get_text())
  
  # Safeguard on Column Titles
  if len(column_names) > 0 and len(column_names) != n_columns:
      raise Exception("Column titles do not match the number of columns")

  columns = column_names if len(column_names) > 0 else range(0,n_columns)
  df = pd.DataFrame(columns = columns,
                    index= range(0,n_rows))
  row_marker = 0
  for row in table.find_all('tr'):
      column_marker = 0
      columns = row.find_all('td')
      for column in columns:
          df.iat[row_marker,column_marker] = column.get_text()
          column_marker += 1
      if len(columns) > 0:
          row_marker += 1

  # Convert to float if possible
  for col in df:
      try:
          df[col] = df[col].astype(float)
      except ValueError:
          pass

  return df

from google.colab import drive
drive.mount('drive')
cmpList = ['TSLA', 'AAPL', 'NFLX']
#https://finance.yahoo.com/quote/%5EIXIC/components?p=%5EIXIC

items = ['', '/analysis']
urlPre = 'https://finance.yahoo.com/quote/'
urlSuf = '?p='

columns = None

#scrappedData = getSummaryData(summaryUrl)
# response = requests.get(financeUrl, verify=False)
# soup = bs.BeautifulSoup(response.text)
# print(soup.prettify())
final_df = pd.DataFrame()

for cmp in cmpList:
  cmp_df_list = []
  print('\nCompany: ', cmp)
  
  for item in items:
    url = urlPre + cmp + item + urlSuf + cmp
    dataframe_list = parse_url(url)
    
    if item is '':
      name = 'summary'
    else:
      name = item[1:len(item)]
    
    print(name, len(dataframe_list), 'tables')
    
    count = 1
    
    item_df = pd.DataFrame()
    
    for df in dataframe_list:
    
      # Summary (2), Analysis (6)
      
      if item is "":
        df = df.transpose()
        item_df = pd.concat([item_df, df], axis = 1, ignore_index = True)
        
        
        
      if item == '/analysis':
        df.set_index(df.columns[0], inplace=True)
        df = df.replace({pd.np.nan: None})
        df = df.unstack().to_frame().sort_index(level=1).T
        df.columns = df.columns.map("_".join)
        item_df = pd.concat([item_df, df], axis = 1)
     
    
    if item is "":
      new_header = item_df.iloc[0] #grab the first row for the header
#       print(item_df)
      item_df.columns = new_header #set the header row as the df header
#       print(item_df)
      item_df = item_df[1:] #take the data less the header row
#       print(item_df)
#       print(new_header)
      item_df.reset_index(inplace=True, drop=True)
     
      
    #print(item_df)
    print(name, item_df.shape[1], 'Columns')
    cmp_df_list.append(item_df)
    
#     filename = cmp + '_' + name + '.csv'
#     item_df.to_csv(filename, index = False)
#     !cp $filename drive/My\ Drive/Isenberg/
  
  
  
  cmp_df = pd.DataFrame()
  for df in cmp_df_list:
    cmp_df = pd.concat([cmp_df,df], axis = 1)
  
  cmp_df.columns = cmp_df.columns.str.replace(cmp, "cmp")
  
  if columns == None:
    columns = cmp_df.columns.tolist()
 
  cmp_df.sort_index(axis=1, inplace=True)

  final_df = pd.concat([final_df, cmp_df], ignore_index = True)

final_df['company'] = cmpList  
final_df = final_df.set_index('company')
print('Final Data: ',final_df.shape)

filename = 'YahooData.csv'
final_df.to_csv(filename)
!cp $filename drive/My\ Drive/Isenberg/

# #listdf = parse_url("https://www.marketwatch.com/investing/stock/aapl/financials")
# listf = parse_url("https://old.nasdaq.com/symbol/aapl/financials?query=balance-sheet")
# for df in listdf:
#   print(df)

from google.colab import drive
drive.mount('drive')
cmpList = ['TSLA', 'AAPL', 'NFLX']
#https://finance.yahoo.com/quote/%5EIXIC/components?p=%5EIXIC

items = ['/financials']
urlPre = 'https://www.marketwatch.com/investing/stock/'

columns = None


final_df = pd.DataFrame()

for cmp in cmpList:
  cmp_df_list = []
  print('\nCompany: ', cmp)
  
  for item in items:
    url = urlPre + cmp + item
    dataframe_list = parse_url(url)
    
    if item is '':
      name = 'summary'
    else:
      name = item[1:len(item)]
    
    print(name, len(dataframe_list), 'tables')
    
    count = 1
    
    item_df = pd.DataFrame()
    
    for df in dataframe_list:
    
      if item is "":
        df = df.transpose()
        item_df = pd.concat([item_df, df], axis = 1, ignore_index = True)
        
        
        
      if item == '/financials':
        df.set_index(df.columns[0], inplace=True)
        df = df.replace({pd.np.nan: None})
        df = df.unstack().to_frame().sort_index(level=1).T
        df.columns = df.columns.map("_".join)
        item_df = pd.concat([item_df, df], axis = 1)
     
    
    if item is "":
      new_header = item_df.iloc[0] #grab the first row for the header
#       print(item_df)
      item_df.columns = new_header #set the header row as the df header
#       print(item_df)
      item_df = item_df[1:] #take the data less the header row
#       print(item_df)
#       print(new_header)
      item_df.reset_index(inplace=True, drop=True)
     
      
    #print(item_df)
    print(name, item_df.shape[1], 'Columns')
    cmp_df_list.append(item_df)
    
#     filename = cmp + '_' + name + '.csv'
#     item_df.to_csv(filename, index = False)
#     !cp $filename drive/My\ Drive/Isenberg/
  
  
  
  cmp_df = pd.DataFrame()
  for df in cmp_df_list:
    cmp_df = pd.concat([cmp_df,df], axis = 1)
  
  cmp_df.columns = cmp_df.columns.str.replace(cmp, "cmp")
  
  if columns == None:
    columns = cmp_df.columns.tolist()
 
  cmp_df.sort_index(axis=1, inplace=True)

  final_df = pd.concat([final_df, cmp_df], ignore_index = True)

final_df['company'] = cmpList  
final_df = final_df.set_index('company')
print('Final Data: ',final_df.shape)

filename = 'MarketWatchData.xlsx'
final_df.to_excel(filename)
!cp $filename drive/My\ Drive/Isenberg/
