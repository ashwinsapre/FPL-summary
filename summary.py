'''
imports
'''
import urllib, json
import urllib.request
import pandas as pd
import dataframe_image as dfi
import unidecode
import logging
logging.basicConfig(filename='app.log', filemode='w',level=logging.INFO)

'''
helper function - removes non-alphanumeric characters from player names, converts accented characters to normal
and truncates long names
'''

def purify(x):
    x = unidecode.unidecode(x)
    x = ''.join(ch for ch in x if ch.isalnum() or ch ==' ')
    if len(x)>25:
        x = x[:25]+'...'
    return x

'''
WORK IN PROGRESS: function to calculate total number of unique players used by a player
'''
#team_url = 'https://fantasy.premierleague.com/api/entry/%d/history/' % 3955
def get_num_unique_players(team_id, end_gw):
    unique_players=[]
    for gw in range(1,end_gw+1):
        team_url=f'https://fantasy.premierleague.com/api/entry/{team_id}/event/{gw}/picks/'
        response = urllib.request.urlopen(team_url)
        data = json.loads(response.read())

        for x in range(15):
            unique_players.append(data.get('picks')[x]['element'])
    return len(set(unique_players))

'''
function to extract team IDs of all league participants
'''
def get_team_ids(league_code):
    teams = {}
    league_url = f'https://fantasy.premierleague.com/api/leagues-classic/{league_code}/standings/?page_standings=1'
    #league_url = 'https://fantasy.premierleague.com/api/leagues-classic/%d/standings/'
    response = urllib.request.urlopen(league_url)
    data = json.loads(response.read())
    if data.get('standings')['has_next']==False:
        for i in range(len(data.get('standings').get('results'))):
            team_id = data.get('standings').get('results')[i].get('entry')
            name = data.get('standings').get('results')[i].get('player_name')
            teams[team_id] = name
        return teams  
    
    else:
        pagenum=1
        while data.get('standings')['has_next']!=False:
            league_url=f'https://fantasy.premierleague.com/api/leagues-classic/{league_code}/standings/?page_standings={pagenum}'
            response = urllib.request.urlopen(league_url)
            data = json.loads(response.read())
            for i in range(len(data.get('standings').get('results'))):
                team_id = data.get('standings').get('results')[i].get('entry')
                name = data.get('standings').get('results')[i].get('player_name')
                teams[team_id] = name
            pagenum+=1
        return teams
    
'''
function to get dataframe containing all info required for a summary table
'''
def get_table(league_code, gw_start, gw_end):
    logging.info(f"========GENERATING NEW SUMMARY========")
    gw_start=gw_start-1
    #API CALL
    teams=get_team_ids(league_code)
    logging.info(f"{len(teams)}team ids fetched")
    rank=0
    prev=-1
    buffer=0
    
    '''
    create skeletal dataframe
    '''
    df = pd.DataFrame(columns=['name', 'points'])
    for team_id in teams.keys():
        '''
        initializing variables inside team loop since they will be unique for each team
        '''
        total, transfers, transfers_cost, bench_points, tv, max_gw_rank, max_rank, max_score = 0,0,0,0,0,0,0,0
        min_gw_rank, min_rank=9000000, 9000000
        min_score=1000
        chiplist = []
        #25 API CALLS
        
        '''
        fetching data for all gws. this data is only fetched once per team.
        '''
        logging.info(f"fetching teamid {team_id}...")
        team_url = 'https://fantasy.premierleague.com/api/entry/%d/history/' % team_id
        response = urllib.request.urlopen(team_url)
        data = json.loads(response.read())
        logging.info(f"...done")
        
        if data.get('chips')!=[]:
            for i in range(len(data.get('chips'))):
                chiplist.append(data.get('chips')[i].get('name'))
                
        '''
        chips used are stored in a list, joined to a string
        '''
        chiplist = [x for x in chiplist if x is not None]
        chips=' '.join(chiplist)
        
        logging.info(f"looping through gws")
        for gw_no in range(gw_start, gw_end):
            try:
                total += data.get('current')[gw_no].get('points') - data.get('current')[gw_no].get('event_transfers_cost')
                transfers_cost += data.get('current')[gw_no].get('event_transfers_cost')
                transfers += data.get('current')[gw_no].get('event_transfers')
                curr_ovr_rank = data.get('current')[gw_no].get('overall_rank')
                if curr_ovr_rank>max_rank:
                    max_rank=curr_ovr_rank
                if curr_ovr_rank<min_rank:
                    min_rank=curr_ovr_rank
                
                gw_score=data.get('current')[gw_no].get('points') - data.get('current')[gw_no].get('event_transfers_cost')
                if gw_score>max_score:
                    max_score=gw_score
                if gw_score<min_score:
                    min_score=gw_score
                
                curr_gw_rank = data.get('current')[gw_no].get('rank')
                if curr_gw_rank>max_gw_rank:
                    max_gw_rank=curr_gw_rank
                if curr_gw_rank<min_gw_rank:
                    min_gw_rank=curr_gw_rank
                
                bench_points+=data.get('current')[gw_no].get('points_on_bench')
                #num_unique_players=get_num_unique_players(team_id, gw_end)                  
                    
            except IndexError:
                total += 0
                transfers+=0
                transfers_cost+=0
                bench_points+=0
  
        if(total!=prev):
            prev=total
            rank+=buffer+1
            buffer=0
        else:
            buffer+=1
        tv=data.get('current')[-1]['value']/10
        cur_rank=data.get('current')[-1].get('overall_rank')
        
        d = pd.DataFrame({'name':teams[team_id], 'points':total, 'rank':cur_rank,'best_overall_rank':min_rank,
                          'worst_overall_rank':max_rank, 'best_gw_rank': min_gw_rank, 'worst_gw_rank':max_gw_rank,
                          'highest_score':max_score, 'lowest_score':min_score,
                          'transfers':transfers, 'transfers_cost':transfers_cost, 
                          'points_on_bench':bench_points, 'chips_used':chips,
                         'team_value':tv}, index=[rank])
        
        df = df.append(d)
    
    df = df.sort_values(['points'], ascending=False)
    return df

def get_summary_image(league_id, max_rows):
    temp=get_table(league_id, 1,19)
    temp=temp.head(max_rows)
    '''
    set index name to rank to prevent column duplication while reading/writing to CSV
    '''
    temp.index.name='rank'
    
    '''
    these columns will be converted to ints
    '''
    int_cols=['rank','best_overall_rank', 'worst_overall_rank',
       'best_gw_rank', 'worst_gw_rank', 'highest_score', 'lowest_score',
       'transfers', 'transfers_cost', 'points_on_bench']
    for col in int_cols:
        temp[col]=temp[col].astype(int)
        temp[col]=temp[col].apply('{:,}'.format)
        
    temp['name']=temp['name'].apply(purify)    
    '''
    exporting backup CSV by the name 'leaguecode+summary.csv'
    '''    
    
    temp.to_csv(f'csvbackups/{league_id}summary.csv')
    logging.info(f"backup created")
    #temp=pd.read_csv(f'csvbackups/{league_id}summary.csv', encoding='utf-8')
    '''
    image stored to separate folder by the name 'leaguecode+summary.png'
    '''
    dfi.export(temp, f'summaryimages/{league_id}summary.png', max_rows=max_rows)
    logging.info(f"summary image exported!")

SMTM=28857
FPLPICT=28853
GHS=13901
RFPL=55331
get_summary_image(RFPL,50)