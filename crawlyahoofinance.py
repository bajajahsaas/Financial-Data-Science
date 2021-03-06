# -*- coding: utf-8 -*-
"""crawlYahooFinance.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1x7PHIK2_iUpHJAfvREiKunlxJOUKTSlw
"""

import bs4 as bs
import urllib.request
import pandas as pd
from time import sleep
from lxml import html  
import requests
import json
import argparse
from collections import OrderedDict
import lxml.html as lh
import copy
import pandas as pd
import urllib3
!pip install --upgrade -q pygsheets
!pip install --upgrade -q gspread
from google.colab import drive
drive.mount('drive')
import gspread
import pygsheets

from google.colab import auth
from oauth2client.client import GoogleCredentials

auth.authenticate_user()
gc = gspread.authorize(GoogleCredentials.get_application_default())
worksheet = gc.open('TICS').sheet1

# get_all_values gives a list of rows.
rows = worksheet.get_all_values()

# Convert to a DataFrame and render.
import pandas as pd
data = pd.DataFrame.from_records(rows, index = None)
cmpList = data[data.columns[0]].astype(str).values.tolist()
print('Number of tickets', len(cmpList))

sleep_val_yahoo = 2
sleep_val = 0

# Brute force way: not used
def getSummaryData(url):
  response = requests.get(url, verify=False)
  print ("Parsing %s"%(url))
  sleep(sleep_val)
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

# for parsing yahoo finance data
#items = ['/financials?p=', '/balance-sheet?p=', '/cash-flow?p=']

financialslen = 5
balancesheetlen = 4
cashflowlen = 5

def getFinanceData(url, name):
  global financialslen
  global balancesheetlen
  global cashflowlen
  try:
    #urllib.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.get(url, verify=False)
    # response = http.request('GET', url)
    sleep(sleep_val_yahoo)
    parser = html.fromstring(response.text)
    finance_table = parser.xpath('//div[contains(@data-test,"fin-row")]')
    
    keys = []
    values = []
    
    columnLen = 0 
    for table_data in finance_table:
      raw_table_key = table_data.xpath('.//span[contains(@class,"Va(m)")]//text()')
      if len(raw_table_key) > 1:
        continue
        
      raw_table_value = table_data.xpath('.//span[not(contains(@class,"Va(m)"))]//text()')
      
      # raw_table_key has only single element
      keys.append(raw_table_key[0])
      values.append(raw_table_value)
      columnLen = max(columnLen, len(raw_table_value))
    
    # Solving mismatch in columns
    if name == 'financials':
      columnLen = financialslen
    
    elif name == 'balance-sheet':
      columnLen = balancesheetlen
    
    elif name == 'cash-flow':
      columnLen = cashflowlen
        
        
    columns = []
    data = []
    
    for row in keys:
      for i in range(1, columnLen + 1):
        columns.append(row + "_" + str(i))
        
    for value in values:
      temp = []
      for item in value:
        temp.append(item)

      if len(value) < columnLen:
        diff = columnLen - len(value)
        while diff > 0:
          temp.append("N/A")
          diff = diff -1
      
      data.extend(temp)
    
    finance_data = pd.DataFrame()
    
    columns_series = pd.Series(columns, index  = None)
    finance_data = pd.DataFrame([data], columns = columns)
    
    return finance_data
  except:
    return pd.DataFrame()

def parse_url(url, cmp):
  try:
    response = requests.get(url)
    sleep(sleep_val)
    soup = bs.BeautifulSoup(response.text, 'lxml')
    
    listdf = []
    
    for table in soup.find_all('table'):
      listdf.append(parse_html_table(table, cmp))
    
    return listdf
  except:
    return []
    
def parse_html_table(table, cmp):
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
              column_names.append(th.get_text().replace(cmp, "cmp"))
  
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

# Brute force way: not used
def getProfileData(url):
  try:
    response = requests.get(url, verify=False)
    print ("Parsing %s"%(url))
    sleep(sleep_val)
    
    parser = html.fromstring(response.text)
    profile_list = parser.xpath('//div[contains(@data-test,"asset-profile")]')
    
    columns = []
    rows = []
    
    
    if len(profile_list) > 0:
      profile_table = profile_list[0] # take the first element (need not iterate)
      address_list = profile_table.xpath('.//p[contains(@class,"D(ib) W(47.727%) Pend(40px)")]//text()')
      address = ""
      for a in address_list:
        address = address + a + " " 

      columns.append("Address")
      rows.append(address)

      info_list = profile_table.xpath('.//p[contains(@class,"D(ib) Va(t)")]//text()')

      for i, val in enumerate(info_list):

        if (i - 1)%3 == 0: # removing junk char
          continue

        if i%3 == 0:
          columns.append(val)
        else:
          rows.append(val)
    
    description_list = parser.xpath('//section[contains(@class,"quote-sub-section Mt(30px)")]')
    if len(description_list) > 0:  
      description_table = description_list[0]
      description = description_table.xpath('.//p[contains(@class,"Mt(15px) Lh(1.6)")]//text()')
      columns.append("Description")
      rows.append(description[0])
    
    corpgov_list = parser.xpath('//section[contains(@class,"Mt(30px) quote-section corporate-governance-container")]')
    if len(corpgov_list) > 0:
      corpgov_table = corpgov_list[0]
      corpgov = corpgov_table.xpath('.//p[contains(@class,"Fz(s)")]//text()')

      columns.append("Corporate Goverance")
      rows.append(corpgov[0])

    
    if len(rows) != len(columns):
      print('Error in profile non tabular data')
      
    finance_data = pd.DataFrame()
    
    columns_series = pd.Series(columns, index  = None)
    profile_data = pd.DataFrame([rows], columns = columns)
    
    
    return profile_data
  
  except:
    return pd.DataFrame()

def writeYahooSummary(cmpList, mode, old_len_df, writer):
  # Parsing data from yahoo finance (profile, analysis, summary)
  print("\nWriting Yahoo Summary")
  towriteCmpList = []
  ignored_cmp = []
  #https://finance.yahoo.com/quote/%5EIXIC/components?p=%5EIXIC

  items = ['']
  urlPre = 'https://finance.yahoo.com/quote/'
  urlSuf = '?p='

  columns = None

  final_df = pd.DataFrame()

  for cmp in cmpList:
    cmp_df_list = []
    print('\nCompany: ', cmp)
    
    for item in items:
      url = urlPre + cmp + item + urlSuf + cmp
      dataframe_list = parse_url(url, cmp)
      
      if item is '':
        name = 'summary'
      else:
        name = item[1:len(item)]
        
      count = 1
      
      item_df = pd.DataFrame()
      
      
      for df in dataframe_list:
      
        # Summary (2), Analysis (6), Profile (1)
        
        
        if item is "":
          df = df.transpose()
          item_df = pd.concat([item_df, df], axis = 1, ignore_index = True)
          
          
        if item == "/analysis": 
          cols_total = df.shape[1]
          column_heads = []
          for head in range(1, cols_total + 1):
            column_heads.append(str(head))
          
          df.columns = column_heads
          
          df.set_index(df.columns[0], inplace=True)
          df = df.replace({pd.np.nan: None})
          df = df.unstack().to_frame().sort_index(level=1).T
          
          df.columns = df.columns.map("_".join)
          
          item_df = pd.concat([item_df, df], axis = 1)
          
      
        if item == "/profile":     
          column_Names = df.columns
          columns = []
          rows = df.shape[0]

          for j in range(1, rows + 1):
            for i in column_Names:
              columns.append(str(i) + "_" + str(j))

          columns_series = pd.Series(columns, index  = None)
          values_series = pd.Series(df.values.flatten(), index = None)
          values_list = [df.values.flatten()]
          item_df = pd.DataFrame(values_list, columns = columns)

      if item is "":
        new_header = item_df.iloc[0] #grab the first row for the header
        item_df.columns = new_header #set the header row as the df header
        item_df = item_df[1:] #take the data less the header row
        item_df.reset_index(inplace=True, drop=True)
      
      
      #print(name, len(dataframe_list), 'tables ', item_df.shape[1], 'Columns')
      cmp_df_list.append(item_df)
      
  #     filename = cmp + '_' + name + '.csv'
  #     item_df.to_csv(filename, index = False)
  #     !cp $filename drive/My\ Drive/AB/
    
    
    # Non tabular Profile 
    profile_url = urlPre + cmp + "/profile" + urlSuf + cmp
    profile_data = getProfileData(profile_url)
    cmp_df_list.append(profile_data)
    
    cmp_df = pd.DataFrame()
    for df in cmp_df_list:
      cmp_df = pd.concat([cmp_df,df], axis = 1)
    
    # Causes problem when company name is "F" and it gets replaced everywhere in the column names. Better to do in parse_url
    # cmp_df.columns = cmp_df.columns.str.replace(cmp, "cmp")
    
    if columns == None:
      columns = cmp_df.columns.tolist()
  
    #cmp_df.sort_index(axis=1, inplace=True) # not required if string replace done at parsing time
    
    if (final_df.shape[0] != 0 and final_df.columns.equals(cmp_df.columns) == False ):
      # except when final_df is empty. This should return always True. Else column mistmatch (ignore this company)
      print('Column mismatch for company: ', cmp, ' Ignoring...')
      #print('differences: ', cmp_df.columns.difference(final_df.columns), final_df.columns.difference(cmp_df.columns)) #should always print 0
      ignored_cmp.append(cmp)
      continue
      # MSFT: has current year (2020): typo
      # ADBE: has different dates
    else:
      towriteCmpList.append(cmp)
    
    
    
    final_df = pd.concat([final_df, cmp_df], ignore_index = True)

  final_df.insert(loc=0, column='company', value=towriteCmpList)
  print('New Data: ',final_df.shape)

  filename = 'YahooSummary.xlsx'
  if mode == "new":
    writer = pd.ExcelWriter(filename, engine='openpyxl')
    final_df.to_excel(writer, index = False)
    len_df  = len(final_df)
  elif mode == "add":
    final_df.to_excel(writer, startrow=old_len_df+1, header=None, index = False)
    len_df = old_len_df + len(final_df)

  writer.save()
  !cp $filename drive/My\ Drive/AB/

  if len(ignored_cmp) > 0:
    ignored_csv = pd.DataFrame(ignored_cmp)
    ignored_filename = 'YahooSummary_ignoredcmp.xlsx'
    ignored_csv.to_excel(ignored_filename, index="False")
    !cp $ignored_filename drive/My\ Drive/AB/
    print('IGNORED COMPANIES: ', len(ignored_cmp))
    raw = input("Enter 't' to retry or 'f' to stop execution")
    if raw == "t":
      writeYahooSummary(ignored_cmp, "add", len_df, writer)
    else:
      return
  else:
    print('IGNORED COMPANIES: ', len(ignored_cmp))

def writeYahooProfile(cmpList, mode, old_len_df, writer):
  # Parsing data from yahoo finance (profile, analysis, summary)
  print("\nWriting Yahoo Profile")
  towriteCmpList = []
  ignored_cmp = []
  #https://finance.yahoo.com/quote/%5EIXIC/components?p=%5EIXIC

  items = ['/profile']
  urlPre = 'https://finance.yahoo.com/quote/'
  urlSuf = '?p='

  columns = None

  final_df = pd.DataFrame()

  for cmp in cmpList:
    cmp_df_list = []
    print('\nCompany: ', cmp)
    
    for item in items:
      url = urlPre + cmp + item + urlSuf + cmp
      dataframe_list = parse_url(url, cmp)
      
      if item is '':
        name = 'summary'
      else:
        name = item[1:len(item)]
        
      count = 1
      
      item_df = pd.DataFrame()
      
      
      for df in dataframe_list:
      
        # Summary (2), Analysis (6), Profile (1)
        
        
        if item is "":
          df = df.transpose()
          item_df = pd.concat([item_df, df], axis = 1, ignore_index = True)
          
          
        if item == "/analysis": 
          cols_total = df.shape[1]
          column_heads = []
          for head in range(1, cols_total + 1):
            column_heads.append(str(head))
          
          df.columns = column_heads
          
          df.set_index(df.columns[0], inplace=True)
          df = df.replace({pd.np.nan: None})
          df = df.unstack().to_frame().sort_index(level=1).T
          
          df.columns = df.columns.map("_".join)
          
          item_df = pd.concat([item_df, df], axis = 1)
          
      
        if item == "/profile":     
          column_Names = df.columns
          columns = []
          rows = df.shape[0]

          for j in range(1, rows + 1):
            for i in column_Names:
              columns.append(str(i) + "_" + str(j))

          columns_series = pd.Series(columns, index  = None)
          values_series = pd.Series(df.values.flatten(), index = None)
          values_list = [df.values.flatten()]
          item_df = pd.DataFrame(values_list, columns = columns)

      if item is "":
        new_header = item_df.iloc[0] #grab the first row for the header
        item_df.columns = new_header #set the header row as the df header
        item_df = item_df[1:] #take the data less the header row
        item_df.reset_index(inplace=True, drop=True)
      
      
      #print(name, len(dataframe_list), 'tables ', item_df.shape[1], 'Columns')
      cmp_df_list.append(item_df)
      
  #     filename = cmp + '_' + name + '.csv'
  #     item_df.to_csv(filename, index = False)
  #     !cp $filename drive/My\ Drive/AB/
    
    
    # Non tabular Profile 
    profile_url = urlPre + cmp + "/profile" + urlSuf + cmp
    profile_data = getProfileData(profile_url)
    cmp_df_list.append(profile_data)
    
    cmp_df = pd.DataFrame()
    for df in cmp_df_list:
      cmp_df = pd.concat([cmp_df,df], axis = 1)
    
    # Causes problem when company name is "F" and it gets replaced everywhere in the column names. Better to do in parse_url
    # cmp_df.columns = cmp_df.columns.str.replace(cmp, "cmp")
    
    if columns == None:
      columns = cmp_df.columns.tolist()
  
    #cmp_df.sort_index(axis=1, inplace=True) # not required if string replace done at parsing time
    
    if (final_df.shape[0] != 0 and final_df.columns.equals(cmp_df.columns) == False ):
      # except when final_df is empty. This should return always True. Else column mistmatch (ignore this company)
      print('Column mismatch for company: ', cmp, ' Ignoring...')
      #print('differences: ', cmp_df.columns.difference(final_df.columns), final_df.columns.difference(cmp_df.columns)) #should always print 0
      ignored_cmp.append(cmp)
      continue
      # MSFT: has current year (2020): typo
      # ADBE: has different dates
    else:
      towriteCmpList.append(cmp)
    
    
    
    final_df = pd.concat([final_df, cmp_df], ignore_index = True)

  final_df.insert(loc=0, column='company', value=towriteCmpList)
  print('New Data: ',final_df.shape)

  filename = 'YahooProfile.xlsx'
  if mode == "new":
    writer = pd.ExcelWriter(filename, engine='openpyxl')
    final_df.to_excel(writer, index = False)
    len_df  = len(final_df)
  elif mode == "add":
    final_df.to_excel(writer, startrow=old_len_df+1, header=None, index = False)
    len_df = old_len_df + len(final_df)

  writer.save()
  !cp $filename drive/My\ Drive/AB/

  if len(ignored_cmp) > 0:
    ignored_csv = pd.DataFrame(ignored_cmp)
    ignored_filename = 'YahooProfile_ignoredcmp.xlsx'
    ignored_csv.to_excel(ignored_filename, index="False")
    !cp $ignored_filename drive/My\ Drive/AB/
    print('IGNORED COMPANIES: ', len(ignored_cmp))
    raw = input("Enter 't' to retry or 'f' to stop execution")
    if raw == "t":
      writeYahooProfile(ignored_cmp, "add", len_df, writer)
    else:
      return
  else:
    print('IGNORED COMPANIES: ', len(ignored_cmp))

def writeYahooAnalysis(cmpList, mode, old_len_df, writer):
  # Parsing data from yahoo finance (profile, analysis, summary)
  print("\nWriting Yahoo Analysis")
  towriteCmpList = []
  ignored_cmp = []
  #https://finance.yahoo.com/quote/%5EIXIC/components?p=%5EIXIC

  items = ['/analysis']
  urlPre = 'https://finance.yahoo.com/quote/'
  urlSuf = '?p='

  columns = None

  final_df = pd.DataFrame()

  for cmp in cmpList:
    cmp_df_list = []
    print('\nCompany: ', cmp)
    
    for item in items:
      url = urlPre + cmp + item + urlSuf + cmp
      dataframe_list = parse_url(url, cmp)
      
      if item is '':
        name = 'summary'
      else:
        name = item[1:len(item)]
        
      count = 1
      
      item_df = pd.DataFrame()
      
      
      for df in dataframe_list:
      
        # Summary (2), Analysis (6), Profile (1)
        
        
        if item is "":
          df = df.transpose()
          item_df = pd.concat([item_df, df], axis = 1, ignore_index = True)
          
          
        if item == "/analysis": 
          cols_total = df.shape[1]
          column_heads = []
          for head in range(1, cols_total + 1):
            column_heads.append(str(head))
          
          df.columns = column_heads
          
          df.set_index(df.columns[0], inplace=True)
          df = df.replace({pd.np.nan: None})
          df = df.unstack().to_frame().sort_index(level=1).T
          
          df.columns = df.columns.map("_".join)
          
          item_df = pd.concat([item_df, df], axis = 1)
          
      
        if item == "/profile":     
          column_Names = df.columns
          columns = []
          rows = df.shape[0]

          for j in range(1, rows + 1):
            for i in column_Names:
              columns.append(str(i) + "_" + str(j))

          columns_series = pd.Series(columns, index  = None)
          values_series = pd.Series(df.values.flatten(), index = None)
          values_list = [df.values.flatten()]
          item_df = pd.DataFrame(values_list, columns = columns)

      if item is "":
        new_header = item_df.iloc[0] #grab the first row for the header
        item_df.columns = new_header #set the header row as the df header
        item_df = item_df[1:] #take the data less the header row
        item_df.reset_index(inplace=True, drop=True)
      
      
      #print(name, len(dataframe_list), 'tables ', item_df.shape[1], 'Columns')
      cmp_df_list.append(item_df)
      
  #     filename = cmp + '_' + name + '.csv'
  #     item_df.to_csv(filename, index = False)
  #     !cp $filename drive/My\ Drive/AB/
    
    
    # Non tabular Profile 
    profile_url = urlPre + cmp + "/profile" + urlSuf + cmp
    profile_data = getProfileData(profile_url)
    cmp_df_list.append(profile_data)
    
    cmp_df = pd.DataFrame()
    for df in cmp_df_list:
      cmp_df = pd.concat([cmp_df,df], axis = 1)
    
    # Causes problem when company name is "F" and it gets replaced everywhere in the column names. Better to do in parse_url
    # cmp_df.columns = cmp_df.columns.str.replace(cmp, "cmp")
    
    if columns == None:
      columns = cmp_df.columns.tolist()
  
    #cmp_df.sort_index(axis=1, inplace=True) # not required if string replace done at parsing time
    
    if (final_df.shape[0] != 0 and final_df.columns.equals(cmp_df.columns) == False ):
      # except when final_df is empty. This should return always True. Else column mistmatch (ignore this company)
      print('Column mismatch for company: ', cmp, ' Ignoring...')
      #print('differences: ', cmp_df.columns.difference(final_df.columns), final_df.columns.difference(cmp_df.columns)) #should always print 0
      ignored_cmp.append(cmp)
      continue
      # MSFT: has current year (2020): typo
      # ADBE: has different dates
    else:
      towriteCmpList.append(cmp)
    
    
    
    final_df = pd.concat([final_df, cmp_df], ignore_index = True)

  final_df.insert(loc=0, column='company', value=towriteCmpList)
  print('New Data: ',final_df.shape)

  filename = 'YahooAnalysis.xlsx'
  if mode == "new":
    writer = pd.ExcelWriter(filename, engine='openpyxl')
    final_df.to_excel(writer, index = False)
    len_df  = len(final_df)
  elif mode == "add":
    final_df.to_excel(writer, startrow=old_len_df+1, header=None, index = False)
    len_df = old_len_df + len(final_df)

  writer.save()
  !cp $filename drive/My\ Drive/AB/

  if len(ignored_cmp) > 0:
    ignored_csv = pd.DataFrame(ignored_cmp)
    ignored_filename = 'YahooAnalysis_ignoredcmp.xlsx'
    ignored_csv.to_excel(ignored_filename, index="False")
    !cp $ignored_filename drive/My\ Drive/AB/
    print('IGNORED COMPANIES: ', len(ignored_cmp))
    raw = input("Enter 't' to retry or 'f' to stop execution")
    if raw == "t":
      writeYahooAnalysis(ignored_cmp, "add", len_df, writer)
    else:
      return
  else:
    print('IGNORED COMPANIES: ', len(ignored_cmp))

# Parsing data from marketwatch (financials)
def writeMarketWatch(cmpList, mode, old_len_df, writer):
  print("\nWriting Market Watch Financials")
  towriteCmpList = []
  ignored_cmp = []
  #https://finance.yahoo.com/quote/%5EIXIC/components?p=%5EIXIC

  items = ['/financials', '/financials/balance-sheet', '/financials/cash-flow']
  # items = ['/financials']
  urlPre = 'https://www.marketwatch.com/investing/stock/'

  columns = None


  final_df = pd.DataFrame()

  for cmp in cmpList:
    cmp_df_list = []
    print('\nCompany: ', cmp)
    
    for item in items:
      url = urlPre + cmp + item
      dataframe_list = parse_url(url, cmp)
      
     
      name = item[1:len(item)]
    
      count = 1
      
      item_df = pd.DataFrame()
      
      for df in dataframe_list:
        cols_total = df.shape[1]
        column_heads = []
        for head in range(cols_total):
          column_heads.append(str(head))
        
        df.columns = column_heads
        df.set_index(df.columns[0], inplace=True)
        df = df.replace({pd.np.nan: None})
        df = df.unstack().to_frame().sort_index(level=1).T
        df.columns = df.columns.map("_".join)
        item_df = pd.concat([item_df, df], axis = 1)
      
    
      # print(item_df)
      # print(name, len(dataframe_list), 'tables ', item_df.shape[1], 'Columns')
      cmp_df_list.append(item_df)
      
  #     filename = cmp + '_' + name + '.csv'
  #     item_df.to_csv(filename, index = False)
  #     !cp $filename drive/My\ Drive/AB/
    
    
    
    cmp_df = pd.DataFrame()
    for df in cmp_df_list:
      cmp_df = pd.concat([cmp_df,df], axis = 1)
    
    # Causes problem when company name is "F" and it gets replaced everywhere in the column names. Better to do in parse_url
    # cmp_df.columns = cmp_df.columns.str.replace(cmp, "cmp")
    
    if columns == None:
      columns = cmp_df.columns.tolist()
  
    #cmp_df.sort_index(axis=1, inplace=True) # not required if string replace done at parsing time
    
    if (final_df.shape[0] != 0 and final_df.columns.equals(cmp_df.columns) == False ):
      # except when final_df is empty. This should return always True. Else column mistmatch (ignore this company)
      print('Column mismatch for company: ', cmp, ' Ignoring...')
      #print('differences: ', cmp_df.columns.difference(final_df.columns), final_df.columns.difference(cmp_df.columns)) #should always print 0
      ignored_cmp.append(cmp)
      continue
      # MSFT: has current year (2020): typo
      # ADBE: has different dates
      # column name different issue fixed. Now different row names causing error
    else:
      towriteCmpList.append(cmp)
    
    
    
    final_df = pd.concat([final_df, cmp_df], ignore_index = True)

  final_df.insert(loc=0, column='company', value=towriteCmpList)
  print('New Data: ',final_df.shape)

  filename = 'MarketWatchFinancials.xlsx'
  if mode == "new":
    writer = pd.ExcelWriter(filename, engine='openpyxl')
    final_df.to_excel(writer, index = False)
    len_df  = len(final_df)
  elif mode == "add":
    final_df.to_excel(writer, startrow=old_len_df+1, header=None, index = False)
    len_df = old_len_df + len(final_df)

  writer.save()
  !cp $filename drive/My\ Drive/AB/

  if len(ignored_cmp) > 0:
    ignored_csv = pd.DataFrame(ignored_cmp)
    ignored_filename = 'MarketWatch_ignoredcmp.xlsx'
    ignored_csv.to_excel(ignored_filename, index="False")
    !cp $ignored_filename drive/My\ Drive/AB/
    print('IGNORED COMPANIES: ', len(ignored_cmp))
    raw = input("Enter 't' to retry or 'f' to stop execution")
    if raw == "t":
      writeMarketWatch(ignored_cmp , "add", len_df, writer)
    else:
      return
  else:
    print('IGNORED COMPANIES: ', len(ignored_cmp))

def writeYahooFinancial(cmpList, mode, old_len_df, writer): 
  # Parsing data from yahoo (financials)
  print("\nWriting Yahoo Financials")
  towriteCmpList = []
  ignored_cmp = []
  finalcolsize = 376

  items = ['/financials?p=', '/balance-sheet?p=', '/cash-flow?p=']
  urlPre = 'https://finance.yahoo.com/quote/'

  columns = None


  final_df = pd.DataFrame()

  for cmp in cmpList:
    cmp_df_list = []
    print('\nCompany: ', cmp)
    
    for item in items:
      url = urlPre + cmp + item + cmp
      # dataframe_list = parse_url(url, cmp)
      
      
      name = item[1:len(item) - 3]
      
      count = 1
      
      item_df = getFinanceData(url, name)
      
    
      print(name, len(item_df), 'table ', item_df.shape[1], 'Columns')
      cmp_df_list.append(item_df)
      
  #     filename = cmp + '_' + name + '.csv'
  #     item_df.to_csv(filename, index = False)
  #     !cp $filename drive/My\ Drive/AB/
    
    
  
    cmp_df = pd.DataFrame()
    for df in cmp_df_list:
      cmp_df = pd.concat([cmp_df,df], axis = 1)
    
    # Causes problem when company name is "F" and it gets replaced everywhere in the column names. Better to do in parse_url
    # cmp_df.columns = cmp_df.columns.str.replace(cmp, "cmp")
    
    if columns == None:
      columns = cmp_df.columns.tolist()
  
    #cmp_df.sort_index(axis=1, inplace=True) # not required if string replace done at parsing time
    
    if final_df.shape[0] == 0:
       if cmp_df.shape[1] != finalcolsize:
        # if first cmp, size of columns should match else exact columns match should return always True. Else column mistmatch (ignore this company)
        print('Column mismatch for company: ', cmp, ' Ignoring...')
        #print('differences: ', cmp_df.columns.difference(final_df.columns), final_df.columns.difference(cmp_df.columns)) #should always print 0
        ignored_cmp.append(cmp)
        continue
      # APPL, TSLA number of columns in balance sheets are different
    elif final_df.columns.equals(cmp_df.columns) == False : 
      print('Column mismatch for company: ', cmp, ' Ignoring...')
      #print('differences: ', cmp_df.columns.difference(final_df.columns), final_df.columns.difference(cmp_df.columns)) #should always print 0
      ignored_cmp.append(cmp)
      continue
    
    
    towriteCmpList.append(cmp)
    final_df = pd.concat([final_df, cmp_df], ignore_index = True)


  final_df.insert(loc=0, column='company', value=towriteCmpList)
  print('New Data: ',final_df.shape)

  filename = 'YahooFinances.xlsx'
  if mode == "new":
    writer = pd.ExcelWriter(filename, engine='openpyxl')
    final_df.to_excel(writer, index = False)
    len_df  = len(final_df)
  elif mode == "add":
    final_df.to_excel(writer, startrow=old_len_df+1, header=None, index = False)
    len_df = old_len_df + len(final_df)

  writer.save()
  !cp $filename drive/My\ Drive/AB/

  if len(ignored_cmp) > 0:
    ignored_csv = pd.DataFrame(ignored_cmp)
    ignored_filename = 'YahooFinances_ignoredcmp.xlsx'
    ignored_csv.to_excel(ignored_filename, index="False")
    !cp $ignored_filename drive/My\ Drive/AB/
    print('IGNORED COMPANIES: ', len(ignored_cmp))
    raw = input("Enter 't' to retry or 'f' to stop execution")
    if raw == "t":
      writeYahooFinancial(ignored_cmp, "add", len_df, writer)
    else:
      return
  else:
    print('IGNORED COMPANIES: ', len(ignored_cmp))

writeYahooFinancial(cmpList, "new", 0, None)
# writeYahooAnalysis(cmpList, "new", 0, None)
# writeYahooSummary(cmpList, "new", 0, None)
# writeYahooProfile(cmpList, "new", 0, None)
# writeMarketWatch(cmpList, "new", 0, None)

'''
import gspread_dataframe as gd

# Connecting with `gspread` here

ws = gc.open("SheetName").worksheet("xyz")
existing = gd.get_as_dataframe(ws)
updated = existing.append(your_new_data)
gd.set_with_dataframe(ws, updated)
'''

# import pandas as pd

# def fun(mode, writer):
#   data = [['tom', 10], ['nick', 15], ['juli', 14]] 
#   # Create the pandas DataFrame 
#   df = pd.DataFrame(data, columns = ['Name', 'Age']) 

#   filename = 'test.xlsx'
  
#   if mode == "new":
#     writer = pd.ExcelWriter(filename, engine='openpyxl')
#     df.to_excel(writer, index=False)
#   else:
#     df.to_excel(writer, startrow=len(df)+1, index=False, header=None)
  
#   writer.save()
#   !cp $filename drive/My\ Drive/AB/
#   return writer


# writer = fun("new", None)
# fun("add", writer)

