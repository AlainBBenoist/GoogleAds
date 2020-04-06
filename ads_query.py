#!/usr/bin/env python
# This program retrieves the keywords used for Google Ads and queries Google Search for the same keywords
# The intent is to identify the websites that are ranking high in terms of SEO for the keywords we buy on Google Ads
#
import sys
import tools
import csv

# Google Ads interface
import google_ads
# Google Search Service
from googleapiclient.discovery import build

class google_stats() :
  DEV_KEY = 'AIzaSyDHAgfYxtpvSbD5YvO93ShQc1ppUdaOhfE'
  CX  = '015498378206524715545:t2ju3w669h8'
  statistics={}

  def search(self, query, max_results, verbose=False) :
    print('S> '+query+ ' '+str(max_results))
    # Build a service object for interacting with the API. Visit
    # the Google APIs Console <http://code.google.com/apis/console>
    # to get an API key for your own application.
    service = build("customsearch", "v1", developerKey=self.DEV_KEY)

    # Determine the number of result pages neeeded 
    rank = 1
    while rank < max_results :
      # Query google for the current page 
      res = service.cse().list(q=query,cx=self.CX,gl='fr',start=rank,hl='fr').execute()
      # Process all results
      for value in res:
          if 'items' not in value:
              continue
          for result in res['items']:
              title = result['title'] if 'title' in result else ''
              url = result['link'] if 'link' in result else ''
              sitename=url.split('/')[2]
              if verbose :
                print('\t{:2d} {:32.32s} {:80.80s}'.format(rank, sitename, url)) 
              # Accumulate statistics 
              if sitename in self.statistics :
                self.statistics[sitename] += 1/rank # 1/Rank is used to provide some form of weighting 
              else :
                self.statistics[sitename] = 1/rank
              rank += 1
    return rank

  def save_stats(self, filename) :
    with open(filename, 'w') as fp :
      # Sort statistics 
      stats = {k: v for k, v in sorted(self.statistics.items(), key=lambda item: item[1], reverse=True)}
      for sitename in stats :
        fp.write('{:s},{:f}\n'.format(sitename, stats[sitename]))
    
def get_reporting(client):
  """
  This function returns a list of keywords from Adwords with their statistics
  """
  csv_filename = "ads_report.csv"
  keywords = {}
  
  report_downloader = client.GetReportDownloader(version='v201809')

  # Report parameters
  report = {
      'reportName': 'KEYWORD_PERFORMANCE_REPORT',
      'dateRangeType': 'ALL_TIME',
      'reportType': 'CRITERIA_PERFORMANCE_REPORT',
      'downloadFormat': 'CSV',
      'selector': {
          'fields': [
            #'CampaignName', 'AdGroupName', 'Id', 'CriteriaType',
                     'Criteria', 'Impressions', 'Clicks', 'Cost', 'Ctr', 'AverageCpc']
      }
  }

  # Download report ro a CSV file 
  with open(csv_filename, 'w') as wfp :
    report_downloader.DownloadReport(report,
                                     wfp,
                                     skip_report_header=True,
                                     skip_column_header=False,
                                     skip_report_summary=True,
                                     include_zero_impressions=True)

  # Read again the CSV file and store keywords in a dict 
  with open(csv_filename, mode='r') as rfp :
    csv_reader = csv.DictReader(rfp)
    for row in csv_reader:
      #print('{:32.32s} {:8.8s} {:s}'.format(row['Keyword / Placement'], row['Impressions'], row['Clicks']))
      if row['Keyword / Placement'] in keywords :
        keywords[row['Keyword / Placement']] += int(row['Clicks'])
      else :
        keywords[row['Keyword / Placement']] = int(row['Clicks'])
        
  # Sort Keywords
  skeywords = {k: v for k, v in sorted(keywords.items(), key=lambda item: item[1], reverse=True)}
  for key in skeywords :
    print('{:40.40s}: {:d}'.format(key, skeywords[key]))
  return skeywords

def get_keywords(googleads) :
  """
  Returns a set of keywords used in Google Ads
  Words are retrieved through APIs
  """
  keywords = set()
  # Retrieve all campaigns, ad groups and related keywords 
  for campaign in googleads.get_campaigns() :
    if campaign['status'] in ['ENABLED', '-----PAUSED'] :
      for ad_group in googleads.get_ad_groups(campaign['id']):
        for keyword in googleads.get_keywords(ad_group['id']) :
          keywords.add(keyword['text'])
          #print('{:40.40s}'.format(keyword['text']), file=sys.stdout if tools.count_words(keyword['text']) > 1 else sys.stderr)
  print('{:d} keywords'.format(len(keywords)))

      
if __name__ == '__main__':

  # Create a Google Ads Interface
  googleads = google_ads.google_ads()

  # Download reporting for goole ads
  keywords = get_reporting(googleads.adwords_client)

  # Create a stats query accumulator
  gs = google_stats()

  keyword_index = 0
  for keyword in keywords :
    if keywords[keyword] > 0 :
      gs.search(keyword, 50, verbose=True)
    keyword_index += 1
    # Self limitation to avoid exceeding API calls limits
    if keyword_index > 10 :
      break

  gs.save_stats('ads_score.csv')

