import sys
from datetime import datetime
from datetime import timedelta
import tools
import events

class evt_container :
    ev = None
    reg_ads = {}
    
    def __init__(self, website, user, app_password) :
        # Load current events
        self.ev = events.events_cache(website, user, app_password)
        self.ev.load_all_events()
        
        # And taxonomies
        self.ev.load_all_taxonomies()

        # Process all events and regroup them by region 
        for event in self.ev.events :
            # Retrieve the region
            try :
                # Fetch the departement
                dept = self.ev.get_region(int(event['region'][0]))['name']
                if ( dept in ['Paris', ] ) :
                    region = dept # make an exception for region where there are numerous events
                else :
                    # Otherwise retrieve the region 
                    region = self.ev.get_region(self.ev.get_region(int(event['region'][0]))['parent'])['name']
            except :
                region = 'unknown'
                print('Region missing for {:s} ({:d})'.format(event['name'], event['id']), file=sys.stderr)
                
            # Add event to the region
            if ( region not in self.reg_ads ) :
                self.reg_ads[region] = {'events' : [], 'cities' : set(), 'keywords' : set(), 'links' : [] }
            self.reg_ads[region]['events'].append(event)

        # And process all events in regions
        for region in self.reg_ads :
            self.proc_region(region) 
        
    def proc_region(self, region) :
        print('{:s}({:d} events)'.format(region, len(self.reg_ads[region]['events'])))
        now = datetime.now()
        now_7days = now + timedelta(days=7)
        evt_ranking = []

        for event in self.reg_ads[region]['events'] :
            start_date = datetime.strptime(event['start_date'][0:10].replace('/', '-'), '%Y-%m-%d')
            end_date = datetime.strptime(event['end_date'][0:10].replace('/', '-'), '%Y-%m-%d')
            if ( start_date > now_7days ) :
                continue   

            # Retrieve event_category
            try : 
                event_category = self.ev.get_taxonomy_term(int(event['eventcat'][0]), 'tribe_events_cat')['name']
            except :
                event_category = ''

            # Retrieve the venue and type of venue            
            venue = self.ev.get_venue(int(event['venue_id']))            
            try : 
                venuetype = self.ev.get_taxonomy_term(int(venue['venuetype'][0]), 'venuetype')['name']
            except :
                venuetype = ''

            # url of the event 
            evt_url = event['evt_url'] if 'evt_url' in event and event['evt_url'] is not None else ''

            # Select events by category
            if ( event_category in ['Expositions', 'Expositions Galeries', 'Grandes Expositions Artistiques à Paris'] ) :
            #if True :
                #print('{:s}\t{:s}\t{:s}\t{:s}\t{:s}\t{:s}\t{:s}\n\t{:s}'.format(event['name'], event['start_date'], event['end_date'], venue['name'],
                #                                                     venue['city'], event_category, venuetype, evt_url))
                # Build a list of cities
                if 'city' in venue :
                    self.reg_ads[region]['cities'].add(venue['city'].strip().lower())

                # Compute a ranking for the event
                sdate = start_date.strftime("%d/%m/%Y")
                edate = end_date.strftime("%d/%m/%Y")
                ranking = self.evt_ranking(event, event_category, venuetype, start_date, end_date)
                evt_ranking.append([ranking, event['name'], event['url'], venue['city'], 'Du '+sdate+' au '+edate, event_category])
                
        # Identifiy the 6 most significant events
        evt_ranking = sorted(evt_ranking, key=lambda ranking: ranking[0], reverse=True)
        for evt_rank in evt_ranking[0:6] :
            link = evt_rank[1:6]
            self.reg_ads[region]['links'].append(link)

    def evt_ranking(self, event, event_category, venuetype, start_date, end_date) :
        now = datetime.now()
        start2now = abs((now - start_date).days)
        end2now = abs((now - end_date).days)
        proximity = min(start2now, end2now)

        ranking = -proximity        
        ranking += 10 if event_category in [ 'Expositions Galeries' ] else 0
        ranking += 100 if event_category in [ 'Expositions' ] else 0
        ranking += 1000 if event_category in [ 'Grandes Expositions Artistiques à Paris' ] else 0
        ranking += 20 if venuetype in ['Musées'] else 0
        ranking += 10 if event['url'] is not None and event['url'] != '' else 0
        try :
            cost = int(event['cost'])
        except :
            cost = 0
        ranking += cost
        #print('Cost='+str(cost)+' Proximity=-'+str(proximity))
        return ranking
        
    def get_regions(self) :
        return [region for region in self.reg_ads]

    def get_region_slug(self, region) :
        result = self.ev.get_region(region)
        if ( result is not None ) :
            return result['slug']

    def get_cities(self, region) :
        return [city for city in self.reg_ads[region]['cities']]

    def get_links(self, region) :
        return [link for link in self.reg_ads[region]['links']]
            

if __name__ == '__main__':
    site_prod = True

    # URL and identifiers of Wordpress site that will receive the events
    website="https://dibutade.fr" if site_prod is True else "http://localhost/wordpress"
    user = "admin9970"
    app_password = b'7WF9 nEFH SRtw EFsM 1vHp Hs7o'

    keywords = ['exposition', 'expo', 'peinture', ]

    # Create an event container
    container = evt_container(website, user, app_password)

    # Print region and cities 
    for region in container.get_regions() :
        print(region+' '+container.get_region_slug(region))
        for link in container.get_links(region) :
            print('\t{:s}\t{:s}\t{:s}\t{:s}\t{:s}'.format(link[0], link[1], link[2], link[3], link[4]))
        print('===================')
        for keyword in keywords :
            for city in container.get_cities(region) :
                print('\t{:s} {:s}'.format(keyword, city))

   
