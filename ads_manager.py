#!/usr/bin/env python
#
import sys
import google_ads
from wordpress_evt import evt_container

# TODO :
# Gestion des ADS
# Extraire les évenements et liens
# Paramtrer annonces avec url region et plusieurs textes
# il serait mieux de remplacer les annonces sans toutes les supprimer
# Sitelinks - les titres qui font plus de 15 caractères sont tronqués
# Will not update budget if it does not match parameter

BUDGET_NAME = 'Budget Régions'
BUDGET_AMOUNT = 100
CPC_AMOUNT = 2
CAMPAIGN_NAME_FMT = '{:s} - Interêt pour {:s}'
AD_URL = 'https://dibutade.fr/events/categorie/expositions/'
AD_URL_FMT = 'https://dibutade.fr/events/region/{:s}/categorie/expositions'
KEYWORDS_FILE_FMT = '{:s}.txt'
TITLE_LENGTH = 25


def update_sitelinks(googleads, campaign_id, new_links) :
  """
  Update the sitelinks of a campaign
  """
  # Retrieve sitelinks associated with the campaign 
  sitelinks = googleads.get_sitelinks(campaign_id)
  print('remove_sitelinks', file=sys.stderr)
  googleads.remove_sitelinks(campaign_id, sitelinks)

  # Create new site sitelinks to Campaign
  print('add_sitelinks', file=sys.stderr)
  googleads.add_sitelinks(campaign_id, new_links)
  
def regional_ads(googleads, evt_category, region, links, ad_group_labels, keywords, cpc=CPC_AMOUNT, target_url=AD_URL) :
  """
  Create and update the Campaign Ads for a given region
  """
  # Retrieve location from Google service
  loc = googleads.search_location(region, 'Region')
  if ( loc is None ) :
    print('Region {:s} not found'.format(region), file=sys.stderr)
    return False
  
  # Retrieve the shared budget
  budget = googleads.get_budget(BUDGET_NAME)
  if not budget :
    budget = googleads.create_budget(BUDGET_NAME, BUDGET_AMOUNT)
    
  # Retrieve campaign if it exists - otherwise create it
  campaign_name=CAMPAIGN_NAME_FMT.format(region, evt_category)
  campaign = googleads.get_campaign(campaign_name)
  if not campaign :
    campaign = googleads.create_campaign(campaign_name, location_id=loc['id'], budget=budget)
  print('Campaign {:s} has Id {:d}'.format(campaign_name, campaign['id']))

  # Update sitelinks
  update_sitelinks(googleads, campaign['id'], links)
  
  # Retrieve the Ad groups of the campaign
  ad_groups = googleads.get_ad_groups(campaign['id'])
  #print(ad_groups)
  # If None was found, create Adgroups 
  if ( ad_groups is None or len(ad_groups) == 0 ) :
    ad_groups = []    # Will contain the new ad_groups
    # Create new Ad Groups from Labels
    print('creating AdGroups', file=sys.stderr)
    for ad_group_label in ad_group_labels :
      ad_group = googleads.add_ad_group(campaign['id'], ad_group_label+' '+region, cpc)
      if ad_group :
        ad_groups.append(ad_group)
        
  # Process all Ad Groups 
  for ad_group in ad_groups:
    print('{:s} {:s}'.format(ad_group['name'], ad_group['status']))
    # 1. KEYWORDS :
    # Retrieve the keywords already active 
    keys = googleads.get_keywords(ad_group['id'])
    for key in keys :
      #print(key)
      if key['text'] not in keywords :
        # Inactivate the corresponding keyword
        googleads.pause_keyword(ad_group['id'], key['id'])
        print('keyword {:s} paused'.format(key['text']))        
      
    # Add keywords to the Ad Groups - no need to worry if they are already present
    print('Adding Keywords', file=sys.stderr)
    for keyword in keywords :
      googleads.add_keyword(ad_group['id'], keyword)

    # 2. ADS  
    # Add Ads to the Ad Group
    ads = googleads.get_ads(ad_group['id'])
    # Handle the case where ads do not exist
    if ads is None or len(ads) == 0 :
      print('Adding Ads', file=sys.stderr)
      ad_desc = ["Toute l'actualité artistique", region, 'Expos Peinture et Sculpture', "Pour les passionné(e)s d'art", "Art Classique, Moderne ou Contemporain, toute l'actualité près de chez vous"]
      ad = googleads.add_ad(ad_group['id'], target_url, ad_desc, [] )
      if ad :
        ads = [ ad, ]
    for ad in ads :
      print('Ad {:d} - {:s},{:s},{:s}'.format(ad['id'], ad['headlinePart1'], ad['headlinePart2'], ad['headlinePart3']))
      
def get_lines(filename) :
  """
  Returns a list of lines from a text file
  """
  file = open(filename,'r')
  lines = file.readlines()
  file.close()
  return [ line.strip() for line in lines ]

def shorten_text(text, length=TITLE_LENGTH) :
  if len(text) <= length :
    return text
  stext = text
##  ok = False
##  while not ok :
##    short_text = input('>> ')
##    ok = True if len(short_text) <= length else False
##  return short_text
  for sep in [':', ',', '-', '«', '.', '–'] :
    stext = stext.split(sep)[0].strip()
  while len(stext) > length :
    print('-- {:s} : {:s}'.format(stext[0:length], text))
    stext = input('-> ')
  return stext

def global_campaigns(googleads) :
  """
  Get a list of global campaigns
  """
  campaign_names = ['Expositions Nationales', ]
  campaigns = list()
  
  for campaign in googleads.get_campaigns() :
    for name in campaign_names :
      if name in campaign['name'] :
        print(campaign['name'])
        links = e.get_links('Paris')
        # Update sitelinks
        update_sitelinks(googleads, campaign['id'], links)   
        continue
  return True

        
if __name__ == '__main__':
  site_prod = True
  evt_category = 'Expositions'
  ad_group_labels = ['Annonces '+evt_category ]
  
  # URL and identifiers of Wordpress site that will receive the events
  website="https://dibutade.fr" if site_prod is True else "http://localhost/wordpress"
  user = "admin9970"
  app_password = b'7WF9 nEFH SRtw EFsM 1vHp Hs7o'

  # Create an event container (wordpress events)
  e = evt_container(website, user, app_password)
  
  # Create a Google Ads Interface
  googleads = google_ads.google_ads()

  print('============= Setting Global Campaigns ==============')
  # Update the sitelinks for global campaigns
  global_campaigns(googleads)
                
  print('============= Setting Campaigns for regions =========')
  
  # Initialize the list of keywords from   file
  basic_keywords = get_lines(KEYWORDS_FILE_FMT.format(evt_category))
  
  for region in e.get_regions() :
    # Check if a region needs to be incorporated
    key = input(region+'? (o/n) :')
    if ( key not in ['o', 'O' ] ) :
      continue
        
    # Create the list of keywords
    keywords = []
    for keyword in basic_keywords :
      # 1. Keyword + region name
      keywords.append(keyword+' '+region.strip().lower())
      # 2. Keyword + cities 
      for city in e.get_cities(region) :
        keywords.append(keyword+' '+city)
        
    # Retrieve the links for the main events in that region 
    links = e.get_links(region)
    
    # Check the links with a title with more than 25 characters
    for link in links :
      link[0] = shorten_text(link[0], length=TITLE_LENGTH)
          
    # Build the target url for the ads of the region
    target_url=AD_URL_FMT.format(e.get_region_slug(region))

    # Update the Google ads campaign for that region including ad groups, sitelinks, keywords
    regional_ads(googleads, evt_category, region, links, ad_group_labels, keywords, target_url=target_url)

    
  
