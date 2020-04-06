#!/usr/bin/env python
#
import sys
import tools
import google_ads

BUDGET_NAME = 'Budget Régions'
BUDGET_AMOUNT = 100
CPC_AMOUNT = 3
CAMPAIGN_NAME_FMT = '{:s} - Interêt pour {:s}'
AD_URL = 'https://dibutade.fr/events/categorie/expositions/'
AD_URL_FMT = 'https://dibutade.fr/events/region/{:s}/categorie/expositions'
KEYWORDS_FILE_FMT = '{:s}.txt'

def report_campaign(googleads, campaign) :
  if campaign['status'] != 'ENABLED' :
    return False
  print('=========================================================================================')
  print('{:48.48s}: id={:d}\tstatus={:s}'.format(campaign['name'], campaign['id'], campaign['status']))
  
  print('Sitelinks:')
  sitelinks=googleads.get_sitelinks(campaign['id'])
  for sitelink in sitelinks :
    if 'sitelinkText' in sitelink :
      text = sitelink['sitelinkText'] if 'sitelinkText' in sitelink and sitelink['sitelinkText'] is not None else ''
      line2 = sitelink['sitelinkLine2'] if 'sitelinkLine2' in sitelink and sitelink['sitelinkLine2'] is not None else ''
      line3 = sitelink['sitelinkLine3'] if 'sitelinkLine3' in sitelink and sitelink['sitelinkLine3'] is not None else ''
      try :
        finalurl = sitelink['sitelinkFinalUrls']['urls'][0]
      except :
        finalurl = ''
      print('\t{:25.25s} {:30.30s} {:30.30s}\t{:40.40s}'.format(text, line2, line3, finalurl))
  print('AdGroups:')
  for ad_group in googleads.get_ad_groups(campaign['id']):
    print('        -------------------------------------------------------------------------------')
    #print(ad_group)
    print('\t{:40.40s}: id={:d}\tstatus={:s}\tBiddingStrategy={:s}'.format(ad_group['name'],
                                                                           ad_group['id'],
                                                                           ad_group['status'],
                                                                           ad_group['biddingStrategyConfiguration']['biddingStrategyType'] ))
    
    print('\tKeywords:')
    impressions = clicks = 0
    for keyword in googleads.get_keywords(ad_group['id']) :
      stats = keyword_stats(keyword['text'])
      print('\t\t{:40.40s}\t{:d}\t{:s}\tI:{:6d}\tC:{:6d}'.format(keyword['text'], keyword['id'], keyword['matchType'], stats['impressions'], stats['clicks']),
                file=sys.stdout if tools.count_words(keyword['text']) > 1 else sys.stderr)
      impressions += stats['impressions']
      clicks += stats['clicks']
    print('\t\t\t\t\t\t\t\t\t\t\tI:{:6d}\tC:{:6d}'.format(impressions, clicks))
    print('\tAds:')
    for ad in googleads.get_ads(ad_group['id']) :
      #print(ad)
      part2 = ad['headlinePart2'] if 'headlinePart2' in ad and ad['headlinePart2'] is not None else ''
      part3 = ad['headlinePart3'] if 'headlinePart3' in ad and ad['headlinePart3'] is not None else ''
      print('\t\t{:24.24s},{:24.24s},{:24.24s},{:40.40s}'.format(ad['headlinePart1'], part2, part3, ad['finalUrls'][0]))

keyword_data = list()
def keyword_stats(keyword) :
  clicks = impressions = cost = 0
  for key in keyword_data :
    if 'Criteria' in key and key['Criteria'] == keyword :
      clicks += int(key['Clicks'])
      impressions += int(key['Impressions'])
      cost += int(key['Cost'])
  return {'keyword' : keyword, 'clicks' : clicks, 'impressions' : impressions, 'cost' : cost }

    
if __name__ == '__main__':
  
  # Create a Google Ads Interface
  googleads = google_ads.google_ads()

  # Create a keyword performance report
  for item in googleads.keyword_performance() :
    keyword_data.append(item)
    #print(item)

  # Retrieve all campaigns
  campaigns = googleads.get_campaigns()
  for campaign in campaigns :
    if campaign['status'] in ['ENABLED', 'PAUSED'] :
      report_campaign(googleads, campaign)


    
  
