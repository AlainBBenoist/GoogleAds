#!/usr/bin/env python
#
# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This example adds campaigns.

To get campaigns, run get_campaigns.py.

The LoadFromStorage method is pulling credentials and properties from a
"googleads.yaml" file. By default, it looks for this file in your home
directory. For more information, see the "Caching authentication information"
section of our README.

"""

"""
TODO:
1) search locations to get a suitable ID
2) parameterize add_ad with various elements of ad (currently hardccoded)
3) Get/Set extensions
4) Check why we don't get results for Manche !!
5° Normalize errors handling 
"""
import sys
import locale
import _locale
import datetime
import uuid
from googleads import adwords
from googleads import errors
import dept_table
from difflib import SequenceMatcher
from pytz import timezone

VERSION = 'v201809'     # API Version
PAGE_SIZE = 100         # Number of Items returned per page

DEF_URL = 'https://dibutade.fr/events'

LANG_FRENCH = '1002'
LANG_ENGLISH = '1000'

LOC_FRANCE = 2250       # Google code for France
ISO_FRANCE = 'FR'

COUNTRY_FRANCE = '2250'
COUNTRY_USA = '2840'
COUNTRY_BELGIUM = '2056'
COUNTRY_SWITZERLAND = '2756'
COUNTRY_ITALY = '2380'
COUNTRY_SPAIN = '2724'
COUNTRY_UK = '2826'

BUDGET_UNIT = 1000000

RANGE_TODAY = 'TODAY'
RANGE_YESTERDAY = 'YESTERDAY'
RANGE_LAST_7_DAYS = 'LAST_7_DAYS'
RANGE_LAST_WEEK = 'LAST_WEEK'
RANGE_LAST_BUSINESS_WEEK = 'LAST_BUSINESS_WEEK'
RANGE_THIS_MONTH = 'THIS_MONTH'
RANGE_LAST_MONTH = 'LAST_MONTH'
RANGE_LAST_14_DAYS = 'LAST_14_DAYS'
RANGE_LAST_30_DAYS = 'LAST_30_DAYS'
RANGE_THIS_WEEK_SUN_TODAY = 'THIS_WEEK_SUN_TODAY'
RANGE_THIS_WEEK_MON_TODAY = 'THIS_WEEK_MON_TODAY'
RANGE_LAST_WEEK_SUN_SAT = 'LAST_WEEK_SUN_SAT'

class google_ads :
  adwords_client = None
  AdServices = {
    'CampaignService' : None,
    'BudgetService' : None,
    'AdGroupService' : None,
    'AdGroupCriterionService' : None,
    'CampaignCriterionService' : None,
    'AdGroupAdService' : None,
    'LocationCriterionService' : None,
    'CampaignExtensionSettingService' : None,
    'CustomerService' : None,
    'TrafficEstimatorService': None,
    'TargetingIdeaService' : None,
  }
  campaigns = []
  budgets = []
  
  def __init__(self) :

    # Set locale encoding to utf-8 for API calls
    _locale._getdefaultlocale = (lambda *args: ['en_US', 'UTF-8'])
    
    # Initialize client object.
    self.adwords_client = adwords.AdWordsClient.LoadFromStorage()

    # Initialize services 
    for service_name in self.AdServices :
      self.AdServices[service_name] = self.adwords_client.GetService(service_name, version=VERSION)
    
    # Load existing campaigns & budgets 
    self.get_campaigns()
    self.get_budgets()

  def googleads_selector(self, service_name, selector) :
    """
    Generic method to iterate from a Google Service (get type)
    """
    service = self.AdServices[service_name]
    
    offset = 0
    # Add paging info to the selector 
    selector['paging'] = {
            'startIndex': str(offset),
            'numberResults': str(PAGE_SIZE)
        }

    more_pages = True
    while more_pages:
      page = service.get(selector)

      # Display results.
      if 'entries' in page:
        for result in page['entries']:
          yield result
      else:
        print('No results were found.', file=sys.stderr)
      offset += PAGE_SIZE
      selector['paging']['startIndex'] = str(offset)
      more_pages = offset < int(page['totalNumEntries'])
      
 #
 # BUDGET MANAGEMENT
 #
  def create_budget(self, budget_name=None, budget_amount=100) :
    """
    Create a budget, which can be shared by multiple campaigns.
    """
    if not budget_name :
      budget_name = 'Budget #%s' % uuid.uuid4()
      
    budget = {
        'name': budget_name,
        'amount': {
            'microAmount': budget_amount*BUDGET_UNIT
        },
        'deliveryMethod': 'STANDARD',
        #'IsBudgetExplicitlyShared' : 'false',
    }

    budget_operations = [{
        'operator': 'ADD',
        'operand': budget
    }]

    # Add the budget.
    try :
      budget = self.AdServices['BudgetService'].mutate(budget_operations)['value'][0]
    except :
      print('Cannot create budget {:s}'.format(budget_name), file=sys.stderr)
      budget = None
    return budget

  def get_budgets(self) :
    """
    Get all budgets
    """
    self.budgets = []
    selector = {
        'fields': ['BudgetId', 'BudgetName', 'Amount', 'IsBudgetExplicitlyShared'],
    }
    for result in self.googleads_selector('BudgetService', selector):
      self.budgets.append(result)
    return self.budgets

  def get_budget(self, budget_name) :
    """
    Get a budget by name
    """
    result = [budget for budget in self.budgets if budget['name'] == budget_name]
    return result[0] if result else None

  def get_budget_by_id(self, budget_id) :
    """
    Get a budget by Id
    """
    result = [budget for budget in self.budgets if budget['id'] == budget_id]
    return result[0] if result else None
  
 #
 # LOCATION MANAGEMENT
 #
  def GetLocationString(self, location):
    return '%s (%s)' % (location['locationName'], location['displayType']
                        if 'displayType' in location else None)

  def search_location(self, location_name, location_type='City'):
    """
    Search locations by name and type on Google 
    It will return the location with the closet name
    """
    #location_names = ['Paris', 'Calvados', 'Aquitaine', 'Provence-Côte d\'Azur']
    ratio_location = 0.0
    best_location = None

    # Create the selector.
    selector = {
        'fields': ['Id', 'LocationName', 'DisplayType', 'CanonicalName',
                   'ParentLocations', 'Reach', 'TargetingStatus'],
        'predicates': [{
            'field': 'LocationName',
            'operator': 'IN',
            'values': [location_name]
        }, {
            'field': 'Locale',
            'operator': 'EQUALS',
            'values': ['fr']
        }]
    }

    # Make the get request.
    location_criteria = self.AdServices['LocationCriterionService'].get(selector)

    # Display the resulting location criteria.
    for location_criterion in location_criteria:
      location = location_criterion['location']
      parent_string = ''
      
      if ('parentLocations' in location and location['parentLocations']):
        parent_string = ', '.join([self.GetLocationString(parent)for parent in location['parentLocations']])
      # Filter on location type
      if ( location['displayType'] == location_type ) :
        # Check if the location is in France
        inFrance = False
        if ('parentLocations' in location and location['parentLocations']):
          for parent_location in location['parentLocations'] :
            if parent_location['displayType'] == 'Country' and parent_location['locationName'] == 'France' :
              inFrance = True
        if inFrance :
          ratio = SequenceMatcher(None,
                                  location_name.strip().lower(),
                                  location['locationName'].strip().lower()).ratio()
          if ( ratio > ratio_location ) :
            ratio_location = ratio
            best_location = location

    return best_location
                        
  def set_location(self, campaign_id, location_id=LOC_FRANCE) :
    """
    Associates a location to a campaign. The Location IDs can be found in the documentation or retrieved with the search_location() method
    The default location_id is for 'France'
    """
    location = {
      'xsi_type': 'Location',
      'id': location_id,
    }
    # Create operations
    operations = [
      {
        'operator': 'ADD',
        'operand': {
            'campaignId': campaign_id,
            'criterion': location,
        }
      },
    ]

    # Make the mutate request.
    result = self.AdServices['CampaignCriterionService'].mutate(operations)

    # Display the resulting campaign criteria.
    for campaign_criterion in result['value']:
      print('Campaign criterion with campaign id "%s", criterion id "%s", '
            'and type "%s" was added.'
            % (campaign_criterion['campaignId'],
                campaign_criterion['criterion']['id'],
                campaign_criterion['criterion']['type']))
 #
 # CAMPAIGN MANAGEMENT
 #
  def get_campaigns(self) :
    """
    Return all campaigns
    """
    self.campaigns = []
    selector = {
        'fields': ['Id', 'Name', 'Status', 'StartDate', 'EndDate', 'BudgetId', 'BudgetName', 'Amount', 'IsBudgetExplicitlyShared', 'FinalUrlSuffix'],
    }
    for result in self.googleads_selector('CampaignService', selector):
      self.campaigns.append(result)
    return self.campaigns

  def get_campaign(self, campaign_name) :
    """
    Get one campaign by name
    """
    result = [campaign for campaign in self.campaigns if campaign['name'] == campaign_name]
    return result[0] if len(result) > 0 else False
  
  def create_campaign(self, campaign_name, budget=None, location_id=LOC_FRANCE):
    """
    Creation of a campaign
    """
    # Look if campaign already exists
    for campaign in self.campaigns :
      if campaign['name'] == campaign_name :
        print('{:s} already exists'.format(campaign_name), file=sys.stderr)
        return False
      
    # Create a budget if none was provided
    if not budget :
      budget = self.create_budget()

    # Construct operations and add campaigns.
    operations = [{
        'operator': 'ADD',
        'operand': {
            'name': campaign_name,
            # Recommendation: Set the campaign to PAUSED when creating it to
            # stop the ads from immediately serving. Set to ENABLED once you've
            # added targeting and the ads are ready to serve.
            'status': 'PAUSED',
            'advertisingChannelType': 'SEARCH',
            'biddingStrategyConfiguration': {
                'biddingStrategyType': 'MANUAL_CPC',
            },
            'endDate': (datetime.datetime.now() +
                        datetime.timedelta(365)).strftime('%Y%m%d'),
            # Note that only the budgetId is required
            #'isExplicitlyShared' : False, (TO TEST) https://developers.google.com/adwords/api/docs/reference/v201809/BudgetService.Budget.html) 
            'budget': {
                'budgetId': budget['budgetId']
            },
            'networkSetting': {
                'targetGoogleSearch': 'true',
                'targetSearchNetwork': 'false',
                'targetContentNetwork': 'false',
                'targetPartnerSearchNetwork': 'false'
            },
            # Optional fields
            'startDate': (datetime.datetime.now() +
                          datetime.timedelta(1)).strftime('%Y%m%d'),
            'frequencyCap': {
                'impressions': '5',
                'timeUnit': 'DAY',
                'level': 'ADGROUP'
            },
            'settings': [
                {
                    'xsi_type': 'GeoTargetTypeSetting',
                    'positiveGeoTargetType': 'DONT_CARE',
                    'negativeGeoTargetType': 'DONT_CARE'
                }
            ]
        }
    },]
    
    try :
      campaigns = self.AdServices['CampaignService'].mutate(operations)['value']
      campaign = campaigns[0]
      print('Campaign with name "{:s}" and id "{:d}" was added.'.format(campaign['name'], campaign['id']))
      # set location
      self.set_location(campaign['id'], location_id)
      return campaign
    except :
      print('Error creating campaign {:s}'.format(campaign_name), file=sys.stderr)
      return False

  def print_campaigns(self) :
    for campaign in self.campaigns :
      print(campaign)
      
 #
 # AD GROUPS MANAGEMENT
 #
  def get_ad_groups(self, campaign_id) :
    """
    Return all AdGroups
    """
    ad_groups = []
    selector = {
        'fields': ['Id', 'Name', 'Status', 'AdGroupType', 'Settings','BiddingStrategyType'], # ,'BiddingStrategyType'
        'predicates': [
            {
                'field': 'CampaignId',
                'operator': 'EQUALS',
                'values': [campaign_id]
            }
        ],
    }
    for result in self.googleads_selector('AdGroupService', selector):
      ad_groups.append(result)
    return ad_groups

  def add_ad_group(self, campaign_id, ad_group_name, cpc_bid) :
    # Construct operations and add ad groups.
    operations = [{
        'operator': 'ADD',
        'operand': {
            'campaignId': campaign_id,
            'name': ad_group_name,
            'status': 'ENABLED',
            'biddingStrategyConfiguration': {
                'bids': [
                    {
                        'xsi_type': 'CpcBid',
                        'bid': {
                            'microAmount': '{:.0f}'.format(cpc_bid*BUDGET_UNIT)
                        },
                    }
                ]
            },
            'settings': [
                {
                    # Targeting restriction settings. Depending on the
                    # criterionTypeGroup value, most TargetingSettingDetail only
                    # affect Display campaigns. However, the
                    # USER_INTEREST_AND_LIST value works for RLSA campaigns -
                    # Search campaigns targeting using a remarketing list.
                    'xsi_type': 'TargetingSetting',
                    'details': [
                        # Restricting to serve ads that match your ad group
                        # placements. This is equivalent to choosing
                        # "Target and bid" in the UI.
                        {
                            'xsi_type': 'TargetingSettingDetail',
                            'criterionTypeGroup': 'PLACEMENT',
                            'targetAll': 'false',
                        },
                        # Using your ad group verticals only for bidding. This is
                        # equivalent to choosing "Bid only" in the UI.
                        {
                            'xsi_type': 'TargetingSettingDetail',
                            'criterionTypeGroup': 'VERTICAL',
                            'targetAll': 'true',
                        },
                    ]
                }
            ]
        }
    }, ]
    try :
      ad_groups = self.AdServices['AdGroupService'].mutate(operations)

      # Display results.
      for ad_group in ad_groups['value']:
        cpc = ad_group['biddingStrategyConfiguration']['bids']['bid']['microAmount']
        print('Ad group with name {:s}, id {:d}, cpc={:f} was added.'.format(ad_group['name'], ad_group['id'], cpc))
        return ad_group
    except :
      print('Error creating AdGroup {:s}'.format(ad_group_name), file=sys.stderr)
      print(ad_groups)
      return False
    
 #
 # KEYWORDS MANAGEMENT
 #
  def get_keywords(self, ad_group_id) :
    keywords = []
    selector = {
        'fields': ['Id', 'CriteriaType', 'KeywordMatchType', 'KeywordText', ],
        'predicates': [
            {
                'field': 'AdGroupId',
                'operator': 'EQUALS',
                'values': [ad_group_id]
            },
            {
                'field': 'CriteriaType',
                'operator': 'EQUALS',
                'values': ['KEYWORD']
            }
        ],
    }
    for result in self.googleads_selector('AdGroupCriterionService', selector):
      keywords.append(result['criterion'])
    return keywords

  def add_keyword(self, adgroup_id, keyword_text, positive_keyword=True, broad_match=True):
    # Construct keyword ad group criterion object.
    keyword = {
        'xsi_type': 'BiddableAdGroupCriterion' if positive_keyword else 'NegativeAdGroupCriterion',
        'adGroupId': adgroup_id,
        'criterion': {
            'xsi_type': 'Keyword',
            'matchType': 'BROAD' if broad_match else 'EXACT', # could also be 'PHRASE'
            'text': keyword_text
        },
        # These fields are optional.
##        'userStatus': 'PAUSED',
##        'finalUrls': {
##            'urls': ['http://example.com/mars']
##        }
    }

    # Construct operations and add ad group criteria.
    operations = [
        {
            'operator': 'ADD',
            'operand': keyword
        },
    ]
    try :
      ad_group_criteria = self.AdServices['AdGroupCriterionService'].mutate(operations)['value']

      # Display results.
      for criterion in ad_group_criteria:
        print('Keyword ad group criterion with ad group id "%s", criterion id '
              '"%s", text "%s", and match type "%s" was added.'
              % (criterion['adGroupId'], criterion['criterion']['id'],
                  criterion['criterion']['text'],
                  criterion['criterion']['matchType']))
    except :
      print('Error adding keyword "{:s}" in adGroup {:d}'.format(keyword_text, adgroup_id), file=sys.stderr)     

  def remove_keyword(self, ad_group_id, keyword_id) :
    # Construct operations and delete ad group criteria.
    operations = [
        {
            'operator': 'REMOVE',
            'operand': {
                'xsi_type': 'BiddableAdGroupCriterion',
                'adGroupId': ad_group_id,
                'criterion': {
                    'id': keyword_id
                }
            }
        }
    ]
    try :
      result = self.AdServices['AdGroupCriterionService'].mutate(operations)

      # Display results.
      for criterion in result['value']:
        print('Criterion Group ID "{:d}", id "{:d}", text "{:s}", type {:s} was deleted.'.format(
          criterion['adGroupId'], criterion['criterion']['id'], criterion['criterion']['text'],criterion['criterion']['Criterion.Type']))
    except :
        print('Keyword "{:d}" could not be removed from AdGroup "{:d}"'.format(keyword_id, ad_group_id), file=sys.stderr)

  def set_keyword(self, ad_group_id, keyword_id, status) :
    # Pause keyword.
    operations = [
        {
            'operator': 'SET',
            'operand': {
                'xsi_type': 'BiddableAdGroupCriterion',
                'adGroupId': ad_group_id,
                'criterion': {
                    'id': keyword_id
                },
                'userStatus': status,
            },
        }
    ]
    try :
      result = self.AdServices['AdGroupCriterionService'].mutate(operations)

      # Display results.
      for criterion in result['value']:
        print('Criterion Group ID "{:d}", id "{:d}", text "{:s}", type {:s} was set to {:s}.'.format(
          criterion['adGroupId'], criterion['criterion']['id'], criterion['criterion']['text'],criterion['criterion']['Criterion.Type'], status))
    except :
        print('Keyword "{:d}" from AdGroup "{:d}" could not be set to {:s}'.format(keyword_id, ad_group_id, status), file=sys.stderr)

  def pause_keyword(self, ad_group_id, keyword_id) :
    # Pause a keyword
    return self.set_keyword(ad_group_id, keyword_id, 'PAUSED')

  def enable_keyword(self, ad_group_id, keyword_id) :
    # Activate a keyword
    return self.set_keyword(ad_group_id, keyword_id, 'ENABLED')
 #
 # SITELINKS MANAGEMENT
 #
  def add_sitelinks(self, campaign_id, sitelinks) :
    if sitelinks is None or len(sitelinks) == 0 :
      return False
    print(sitelinks)
    extensions = [{
          'xsi_type': 'SitelinkFeedItem',
          'sitelinkText': sitelink[0][0:25],
          'sitelinkFinalUrls': {'urls': [ sitelink[1] ]},
          'sitelinkLine2' : sitelink[2][0:35] if len(sitelink) > 2 else '',
          'sitelinkLine3' : sitelink[3][0:35] if len(sitelink) > 3 else '' } for sitelink in sitelinks]
    
##    for sitelink in sitelinks :
##      extensions.append({
##          'xsi_type': 'SitelinkFeedItem',
##          'sitelinkText': sitelink[0][0:25],
##          'sitelinkFinalUrls': {'urls': [ sitelink[1] ]},
##          'sitelinkLine2' : sitelink[2][0:35] if len(sitelink) > 2 else '',
##          'sitelinkLine3' : sitelink[3][0:35] if len(sitelink) > 3 else '' })


    operation = {
        'operator': 'ADD',
        'operand': {
          'campaignId': campaign_id,
          'extensionType': 'SITELINK',
          'extensionSetting': {
            'extensions': extensions,
          }
      }
    }
    #print(operation)
    # Add the extensions.
    response = self.AdServices['CampaignExtensionSettingService'].mutate([operation])

    if 'value' in response:
      print('Extension setting with type "%s" was added to campaignId "%d".' %
            (response['value'][0]['extensionType'],
             response['value'][0]['campaignId']))
      return True
    else:
      raise errors.GoogleAdsError('No extension settings were added.')
      print(sitelinks)
    return False
    
  def get_sitelinks(self, campaign_id) :
    """
    Return all sitelinks for a campaign_id
    """
    sitelinks = []
    selector = {
        'fields': ['CampaignId', 'ExtensionType', 'Extensions'],
        'predicates': [
            {
                'field': 'CampaignId',
                'operator': 'EQUALS',
                'values': [campaign_id]
            }, 
        ],
    }
    try :
      for result in self.googleads_selector('CampaignExtensionSettingService', selector):
        for extension in result['extensionSetting']['extensions'] :
          sitelinks.append(extension)
    except :
      print('No sitelinks for campaign {:d}'.format(campaign_id), file=sys.stderr)
    return sitelinks

  def remove_sitelinks(self, campaign_id, extensions) :
    if extensions is None or len(extensions) == 0 :
      return False
    operation = {
        'operator': 'REMOVE',
        'operand': {
          'campaignId': campaign_id,
          'extensionType': 'SITELINK',
          'extensionSetting': {
            'extensions': extensions,
          }
      }
    }
    #print(operation)
    # Delete the extensions.
    response = self.AdServices['CampaignExtensionSettingService'].mutate([operation])

    if 'value' in response:
      print('Extension setting with type "%s" was deleted to campaignId "%d".' %
            (response['value'][0]['extensionType'],
             response['value'][0]['campaignId']))
    else:
      raise errors.GoogleAdsError('No extension settings were added.')    
    return False
    
  #
  # ADS MANAGEMENT
  #
  def get_ads(self, ad_group_id) :
    """
    Get all Ads for a given AdGroup
    """
    ads = []
    selector = {
        'fields': ['Id', 'AdGroupId', 'Status',
                   'HeadlinePart1', 'HeadlinePart2', 'ExpandedTextAdHeadlinePart3',
                   'Description', 'ExpandedTextAdDescription2',
                   'Path1', 'Path2',
                   'CreativeFinalUrls',],
        'predicates': [
            {
                'field': 'AdGroupId',
                'operator': 'EQUALS',
                'values': [ad_group_id]
            },
            {
                'field': 'AdType',
                'operator': 'EQUALS',
                'values': ['EXPANDED_TEXT_AD']
            }
        ],
        'ordering': [
            {
                'field': 'Id',
                'sortOrder': 'ASCENDING'
            }
        ]
    }
    for result in self.googleads_selector('AdGroupAdService', selector):
      ads.append(result['ad'])
    return ads
  
  def add_ad(self, ad_group_id, url=None, ad=[], path=[]):
    """
    Add an AD to an Ag Group
    """
    if ad is None or len(ad) == 0 :
      return False

    operations = [
        {
            'operator': 'ADD',
            'operand': {
                'xsi_type': 'AdGroupAd',
                'adGroupId': ad_group_id,
                'ad': {
                    'xsi_type': 'ExpandedTextAd',
                    'headlinePart1': ad[0][0:30],
                    'headlinePart2': ad[1][0:30] if len(ad) > 1 else '',
                    'headlinePart3': ad[2][0:30] if len(ad) > 2 else '',
                    'description': ad[3][0:90] if len(ad) > 3 else '',
                    'description2': ad[4][0:90] if len(ad) > 4 else '',
                    'finalUrls': [DEF_URL if url is None else url],
                    'path1' : path[0][0:15] if len(path) > 0 else '',
                    'path2' : path[1][0:15] if len(path) > 1 else ''
                },
                # Optional fields.
                'status': 'ENABLED'
            }
        }
    ]
    try : 
      result = self.AdServices['AdGroupAdService'].mutate(operations)

      # Display results.
      for ad in result['value']:
        print('Ad "{:s}" with id "{:d}" was added.\n\theadlinePart1: {:s}\n\theadlinePart2: {:s}\n\theadlinePart3: {:s}\n\tdescription: {:s}'.format(
          ad['ad']['Ad.Type'], ad['ad']['id'], ad['ad']['headlinePart1'], ad['ad']['headlinePart2'], ad['ad']['headlinePart3'], ad['ad']['description']))
        return ad
    except :
      print('Error adding ad in adGroup {:d}'.format(ad_group_id), file=sys.stderr)
    return False
      
  def set_ad(self, ad_group_id, ad_id, status) :
    """
    Modify status of an ad
    """
    # Construct operations and update an ad.
    operations = [{
        'operator': 'SET',
        'operand': {
            'adGroupId': ad_group_id,
            'ad': {
                'id': ad_id,
            },
            'status': status,
        }
    }]
    ads = self.AdServices['AdGroupAdService'].mutate(operations)

    # Display results.
    for ad in ads['value']:
      print('Ad with id "%s" was updated.'% ad['ad']['id'])
      return ad
    return False
  
  def pause_ad(self, ad_group_id, ad_id) :
    """
    Pause an ad
    """
    return self.set_ad(ad_group_id, ad_id, 'PAUSED')

  def enable_ad(self, ad_group_id, ad_id) :
    """
    Enable an ad
    """
    return self.set_ad(ad_group_id, ad_id, 'ENABLED')

  def remove_ad(self, ad_group_id, ad_id) :
    """
    Remove an ad
    """
    # Construct operations and delete ad.
    operations = [{
        'operator': 'REMOVE',
        'operand': {
            'xsi_type': 'AdGroupAd',
            'adGroupId': ad_group_id,
            'ad': {
                'id': ad_id
            }
        }
    }]
    result = self.AdServices['AdGroupAdService'].mutate(operations)

    # Display results.
    for ad in result['value']:
      print('Ad with id "%s" and type "%s" was deleted.' % (ad['ad']['id'], ad['ad']['Ad.Type']))
      return True
    return False

  def keyword_estimate(self, keywords):
    """
    Calculate estimates of Click rates and costs for a list of keywords
    """
    
    # Construct selector object and retrieve traffic estimates.
    keyword_estimate_requests = []
    for keyword in keywords:
      keyword_estimate_requests.append({
          'keyword': {
              'xsi_type': 'Keyword',
              'matchType': keyword['matchType'],
              'text': keyword['text']
          }
      })

    # Create ad group estimate requests.
    adgroup_estimate_requests = [{
        'keywordEstimateRequests': keyword_estimate_requests,
        'maxCpc': {
            'xsi_type': 'Money',
            'microAmount': '1000000'
        }
    }]

    # Create campaign estimate requests.
    campaign_estimate_requests = [{
        'adGroupEstimateRequests': adgroup_estimate_requests,
        'criteria': [
            {
                'xsi_type': 'Location',
                'id': '2250'  # France.
            },
            {
                'xsi_type': 'Language',
                'id': '1002'  # France.
            }
        ],
    }]

    # Create the selector.
    selector = {
        'campaignEstimateRequests': campaign_estimate_requests,
    }

    # Optional: Request a list of campaign-level estimates segmented by
    # platform.
    selector['platformEstimateRequested'] = False

    # Get traffic estimates.
    estimates = self.AdServices['TrafficEstimatorService'].get(selector)

    campaign_estimate = estimates['campaignEstimates'][0]

    # Display the keyword estimates.
    result_lst = []
    if 'adGroupEstimates' in campaign_estimate:
      ad_group_estimate = campaign_estimate['adGroupEstimates'][0]
      if 'keywordEstimates' in ad_group_estimate:
        keyword_estimates = ad_group_estimate['keywordEstimates']

        keyword_estimates_and_requests = zip(keyword_estimates, keyword_estimate_requests)
        
        for keyword_tuple in keyword_estimates_and_requests:   
          keyword = keyword_tuple[1]['keyword']
          keyword_estimate = keyword_tuple[0]
          if not keyword_estimate :
            continue
          
          result = {'keyword' : keyword['text'], 'matchType' : keyword['matchType'] }
          for indicator in ['averagePosition', 'clicksPerDay'] :
            if indicator in keyword_estimate['min'] and indicator in keyword_estimate['max'] : 
              min_est, max_est = (keyword_estimate['min'][indicator], keyword_estimate['max'][indicator]) 
              result[indicator] = (float(min_est) + float(max_est)) / 2.0 if min_est and max_est else None
            else :
              result[indicator] = None
            
          for indicator in ['averageCpc', 'totalCost' ] :
            if indicator in keyword_estimate['min'] and indicator in keyword_estimate['max'] and keyword_estimate['min'][indicator]: 
              min_est, max_est = (keyword_estimate['min'][indicator]['microAmount'], keyword_estimate['max'][indicator]['microAmount']) 
              result[indicator] = (float(min_est) + float(max_est)) / (2.0 * BUDGET_UNIT) if min_est and max_est else None
            else :
              result[indicator] = None
              
          result_lst.append(result)
          
    return result_lst


  def keyword_ideas(self, ad_group_id, queries):
    """
    Retrieve keyword ideas
    """

    # Construct selector object and retrieve related keywords.
    selector = {
        'ideaType': 'KEYWORD',
        'requestType': 'IDEAS',
        'requestedAttributeTypes': [
              'KEYWORD_TEXT', 'SEARCH_VOLUME', 'CATEGORY_PRODUCTS_AND_SERVICES'
        ],
        'searchParameters' : [
          {'xsi_type': 'RelatedToQuerySearchParameter', 'queries': queries },
          {'xsi_type': 'LanguageSearchParameter', 'languages': [{'id': LANG_FRENCH}]},
          {'xsi_type': 'NetworkSearchParameter', 'networkSetting': {
            'targetGoogleSearch': True,
            'targetSearchNetwork': False,
            'targetContentNetwork': False,
            'targetPartnerSearchNetwork': False },
          },
        ]
      }

    # Use an existing ad group to generate ideas (optional)
    if ad_group_id is not None:
      selector['searchParameters'].append({
          'xsi_type': 'SeedAdGroupIdSearchParameter',
          'adGroupId': ad_group_id
      })

    ideas = []
    imap = {'KEYWORD_TEXT' : 'keyword', 'SEARCH_VOLUME' : 'volume', 'CATEGORY_PRODUCTS_AND_SERVICES' : 'categories' }
    for result in self.googleads_selector('TargetingIdeaService', selector):
        if result and 'data' in result :
          idea = dict()
          for item in result['data'] :
            idea[imap[item['key']]] = item['value']['value']
        ideas.append(idea)
    return ideas

  def keyword_performance(self, date_range=RANGE_LAST_30_DAYS):
    """
    """
    fields = ['CampaignId', 'CampaignName', 'AdGroupId', 'AdGroupName', 'Id', 'CriteriaType',
              'Criteria', 'FinalUrls', 'Impressions', 'Clicks', 'Cost']
    report_downloader = self.adwords_client.GetReportDownloader(version=VERSION)

    # Create report definition.
    report = {
        'reportName': 'Last 30 days CRITERIA_PERFORMANCE_REPORT',
        'dateRangeType': date_range,
        'reportType': 'CRITERIA_PERFORMANCE_REPORT',
        'downloadFormat': 'CSV',
        'selector': {
            'fields': fields
        }
    }
    # Retrieve the report as a string.
    data = report_downloader.DownloadReportAsString(
      report, skip_report_header=True, skip_column_header=True,
      skip_report_summary=True, include_zero_impressions=True)

    # Process each line 
    for line in data.split('\n') :
      items = line.split(',')
      # Build a dictionnary with the results 
      yield dict(zip(fields, items))

if __name__ == '__main__':
  # Set locale encoding to utf-8 for API calls
  _locale._getdefaultlocale = (lambda *args: ['en_US', 'UTF-8'])


  search_keywords = [
        {'text': 'expo paris', 'matchType': 'BROAD'},
        {'text': 'expo banksy', 'matchType': 'BROAD'},
        {'text': 'expo grand palais', 'matchType': 'BROAD'}
  ]
  idea_keywords = ['stage peinture', 'stage aquarelle', 'stage sculpture', 'stage dessin']
  
  ad_group_labels = ['Annonces expo', 'Annonces musées']
  keywords = ['exposition', 'expo',    ]
  links = [ ('Exposition Picasso', 'https://dibutade.fr/event/exposition-picasso', 'Janvier 2020', 'Réservations en ligne' ),
            ('Exposition Toulouse-Lautrec','https://dibutade.fr/exposition-toulouse-lautrec' ), ]
  ad_labels = [ "Expositions artistiques", "Toute l'actualité culturelle", "Dans votre région", "Agenda constamment remis à jour", "" ]  

  # Create the Google Ads Interface
  a = google_ads()

  # Print keywords estimates
  for key in a.keyword_performance() :
    print(key)
    
  result=a.keyword_estimate(search_keywords)
  print(result)
  result=a.keyword_ideas(49221764877, idea_keywords)
  print(result)
  key = input('Continue:')
  
  print('============== Campaigns ================')
  for campaign in a.get_campaigns() :
    print(campaign)
    print('{:s} : {:d} - {:s}'.format(campaign['name'], campaign['id'],campaign['status']))
  print('============== Campaigns ================')
  print(a.get_budgets())
  #agenda expos grand-est
  print(a.pause_keyword(83373509016,321258728106))
  #keyw = a.get_keywords(86893793167)
  #print(a.enable_keyword(86893793167,328941264161))
  key=input('Continue')
  
  print('============= Setting Campaigns =========')
  for region in ['Corse'] :
    # Retrieve shared budget
    budget = a.get_budget('Budget '+region)
    print(budget)
    # Retrieve location
    loc = a.search_location(region, 'Region')
    print(loc)
    
    # Retrieve campaign if it exists - otherwise create it 
    campaign = a.get_campaign('Expositions '+region)
    if not campaign :
      campaign = a.create_campaign('Expositions '+region, location_id=loc['id'], budget_id=budget['budgetId'])
    print('Campaign Expositions {:s} has Id {:d}'.format(region, campaign['id']))
    sitelinks = a.get_sitelinks(campaign['id'])
    
    #a.remove_sitelinks(campaign_id, sitelinks)

    # Add sitelinks to Campaign
    a.add_sitelinks(campaign['id'], links)
    
    # Retrieve the Ad groups of the campaign
    ad_groups = a.get_ad_groups(campaign['id'])
    # If None was found, create them
    if ( len(ad_groups) == 0 ) :
      ad_groups = []
      # Create new Ad Groups from Labels 
      for ad_group_label in ad_groups_labels :
        ad_group = a.add_ad_group(campaign['id'], ad_group_label+region, 3)
        if ad_group :
          ad_groups.append(ad_group)
          
    # Process all Ad Groups 
    for ad_group in ad_groups:
      # KEYWORDS :
      # Retrieve the keywords already active 
      keys = a.get_keywords(ad_group['id'])
      for key in keys :
        if key['text'] not in keywords :
          # Inactivate the corresponding keyword
          a.pause_keyword(ad_group['id'], key['id'])
        
      # Add keywords to the Ad Groups - no need to worry if they are already present
      for keyword in keywords :
        a.add_keyword(ad_group['id'], keyword)

      # ADS  
      # Add Ads to the Ad Group
      for ad in a.get_ads(ad_group['id']) :
        print(ad)
      a.add_ad(ad_group['id'], url = DEF_URL, ad=ad_labels, path=[])
    
  
