#!/usr/bin/env python
#
import sys
import codecs
import csv

import tools
import google_ads

def campaign_report(googleads, campaign, kreport) :
    """
    Report Keywords for a given campaign
    """
    #print(campaign)
    for ad_group in googleads.get_ad_groups(campaign['id']):
        for keyword in googleads.get_keywords(ad_group['id']) :
            # Retrieve actual performance on our website
            stats = kreport.stats(campaign['id'], ad_group['id'], keyword['text'])
            if stats['clicks'] <= 0 :
                continue
            # Retrieve estimates for that keyword
            r_cpc = dict()
            r_cost = dict()
            r_position = dict()
            r_clicks = dict()
            for match_type in ['BROAD', 'EXACT', 'PHRASE' ] :
                est_cpc = est_cost = est_position = est_clicks_day = est_clicks = 0
                keyword_est = googleads.keyword_estimate([{'text' : keyword['text'], 'matchType' : match_type}])
                if keyword_est and len(keyword_est) > 0 :
                    estim = keyword_est[0]
                    est_cpc = estim['averageCpc']
                    est_clicks_day = estim['clicksPerDay']                    
                    #est_cpc, est_cost, est_position, est_clicks_day = (estim['averageCpc'], estim['totalCost'], estim['averagePosition'], estim['clicksPerDay'])
                    est_clicks = est_clicks_day * 30 if type(est_clicks_day) is int else 0
                    est_cpc = est_cpc if type(est_cpc) is float else 0

                r_cpc[match_type] = est_cpc
                r_clicks[match_type] = est_clicks


            #r_cpc[match_type], r_position[match_type], r_cost[match_type], r_clicks[match_type] = (est_cpc, est_position, est_cost, est_clicks)
            yield ({'campaign_name' : campaign['name'],
                  'adgroup_name'  : ad_group['name'],
                  'keyword'       : keyword['text'],
                  'match_type'    : keyword['matchType'],
                  'clicks'        : stats['clicks'],
                  'impressions'   : stats['impressions'],
                  'cost'          : stats['cost'],
                  'cpc'           : stats['cost']/stats['clicks'] if stats['clicks'] > 0 else 0,
                  'est_cpc_BROAD' :   r_cpc['BROAD'],
                  'est_clicks_BROAD': r_clicks['BROAD'],
                  'est_cpc_EXACT' :   r_cpc['EXACT'],
                  'est_clicks_EXACT': r_clicks['EXACT'],
                  'est_cpc_PHRASE':   r_cpc['PHRASE'],
                  'est_clicks_PHRASE': r_clicks['PHRASE']})
              
              


class keyword_report() :
    """
    Class to generate and access data in a report
    """
    report = None
  
    def __init__(self, googleads) :
        # Create a keyword performance report
        self.report = list()
        for item in googleads.keyword_performance() :
            self.report.append(item)

    def keywords(self) :
        for line in self.report :
            if 'Criteria' in line :
                yield line['Criteria']
        return None

    def stats(self, campaign_id, adgroup_id, keyword) :
        """
        Returns statistics for a given keyword in a report
        """
        #print(campaign_id)
        clicks = impressions = cost = 0
        for line in self.report :
            #print(line)
            #key=input('continue')
            if ('Criteria' in line and line['Criteria'] == keyword
                and line['CampaignId'] == str(campaign_id)
                and line['AdGroupId'] == str(adgroup_id) ) :
                clicks += int(line['Clicks'])
                impressions += int(line['Impressions'])
                cost += float(line['Cost'])/1000000
        return {'campaign_id' : campaign_id,
                'adgroup_id' : adgroup_id,
                'keyword' : keyword,
                'clicks' : clicks,
                'impressions' : impressions,
                'cost' : cost }

    
if __name__ == '__main__':
  
  # Create a Google Ads Interface
  googleads = google_ads.google_ads()

  # Create a keyword report
  report = keyword_report(googleads)

  # Retrieve all campaigns
  campaigns = googleads.get_campaigns()

  # Create a csv file for the results
  filename='keyword_analysis.csv'
  with codecs.open(filename, 'w', "utf-8") as csvfile:
    fieldnames = ['campaign_name', 'adgroup_name', 'keyword', 'match_type', 'clicks', 'impressions', 'cost', 'cpc', 'est_cpc_BROAD', 'est_clicks_BROAD', 'est_cpc_EXACT', 'est_clicks_EXACT','est_cpc_PHRASE', 'est_clicks_PHRASE' ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, restval='', extrasaction='ignore', delimiter=';', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
    writer.writeheader()
    
    for campaign in campaigns :
      if campaign['status'] not in ['ENABLED'] :
        continue
    
      # report keywords 
      for data in campaign_report(googleads, campaign, report) :
        writer.writerow(data)
        print('{:23.23s}\t{:20.20s}\t{:40.40s}\t{:s}\t{:d}\t{:d}\t{:3.2f}\t{:3.2f}\t{:2.2f}\t{:2.2f}'.format(
                                                                  data['campaign_name'],
                                                                  data['adgroup_name'],
                                                                  data['keyword'],
                                                                  data['match_type'],
                                                                  data['clicks'],
                                                                  data['impressions'],
                                                                  data['cost'],
                                                                  data['cpc'],
                                                                  data['est_cpc_BROAD'],
                                                                  data['est_clicks_BROAD']), file=sys.stdout if tools.count_words(data['keyword']) > 1 else sys.stderr)

  
  
