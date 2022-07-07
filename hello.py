"""
Document for blah
"""
from platform import release
import xml.etree.ElementTree as ET
import requests
import os
import re
import sys
import json
from relval import RelVal
from relmon import Relmon



def get_releases():
    """
    This function takes the xml content from the given URL, it changes it to array of tuples
    and sorts them according to the version of the CMSSW. Every tuple is structured like:
    name of the architecture, label, type and state.
    """


    url = "https://cmssdt.cern.ch/SDT/cgi-bin/ReleasesXML?anytype=1"

    file2 = requests.get(url)

    file1 = open("content.txt", "w")
    file1.write(file2.content.decode())

    tree = ET.parse('content.txt')
    root = tree.getroot()

    arr = []

    for child1 in root:
        if child1.tag == 'architecture':
            for child2 in child1:
                if child2.tag == 'project':
                    name = child1.get('name')
                    label = child2.get('label')
                    tip = child2.get('type')
                    state = child2.get('state')

                    release = tuple((name, label, tip, state))
                    arr.append(release)

    arr_sort = []
    arr_sort = sorted(arr, key=lambda x: tuple(int(i) for i in  x[1].split('_')[1:4]))
    return arr_sort    

releases = get_releases()
new = []
old = []
new_tickets = []


def new_releases(releases):
    """
    This function checks for new releases that follow the PATTERN, checks the existance of old.txt file,
    puts new releases into new[] and new.txt and also updates old.txt file
    """
    global old
    global new

    #pattern = 'CMSSW(_\d{1,2}){2}_0(_pre([2-9]|(\d{2,10})))?$'
    #The regex for catching all the first releases and pres
    pattern = 'CMSSW(_\d{1,2}){2}_0(_pre([2-9]|(\d{2,10})))+$'
    #The regex for fetching all the pres
    
    
    releases = [x for x in releases if re.match(pattern, x[1])]
    #This is taking away all the releases that don't match the regex


    if not os.path.exists('old.txt'):
        with open('old.txt', 'w') as output_file:
            for x in releases:
                if re.match(pattern, x[1]):
                    output_file.write(x[1] + '\n')
        sys.exit(0)
    #If there exists no OLD.TXT file

    old_str = open('old.txt', 'r')

    old = old_str.read().split('\n')
    old.remove('')
    old_sorted = []
    old_sorted = sorted(old, key=lambda x: tuple(int(i) for i in re.findall('\d+', x)))
    #Sorting old releases. x is a string, example: x="CMSSW_12_1_0_pre3" and
    #list is sorted by numbers from left to right
    old = old_sorted

       
    for x in releases:
        if x[1] not in old:
            new.append(x)           #appending new releases to the list new[]
    ### Sljedeca linija je iskljucivo zbog probe
    #new.append(releases[-1])


    with open('new.txt', 'w') as output_file:
        for x in new:
            output_file.write(x[1] + '\n')          #Putting new releases into file

    with open('old.txt', 'w') as input_file:
        for x in releases:
            input_file.write(x[1] + '\n')           #Updating old releases for next iteration

def relvals_creation(new):
    
    if len(new) == 0:       #If the new releases list is empty then there are no new releases
        print('There are no new releases')
        sys.exit(1)
    else:
        #Otherwise, we will need a relval class
        relval = RelVal()

        #old_tickets = relval.get('tickets', query='cmssw_release=' + old[-1])
        old_tickets = relval.get('tickets', query='cmssw_release=CMSSW_12_0_0_pre*')
        #This line gets all old tickets with specified query
        old_tickets_sort = sorted(old_tickets, key=lambda x: tuple(int(i) for i in  x['_id'].split('pre')[1].split('__')[0]))
        print(len(old_tickets_sort))


        tickets_to_be_pushed = []
        #REGEX FOR TICKETS WITHOUT noPU                           ^((?!noPU).)*$
        #REGEX FOR TICKETS WITH noPU                               .*(noPU)+.*$
        for old_ticket in old_tickets_sort:
            ticket = old_ticket
            ticket['cmssw_release'] = new[0][1]
            ticket['batch_name'] = old_ticket['batch_name'] + '_AUTOMATED_CREATION'
            tickets_to_be_pushed.append(ticket)
        #New tickets have the same values besides 'cmssw_release'
        ######################################################################################
        with_noPU = ".*(noPU)+.*$"
        with_PU = ".*(PU)+.*$"
        PU_array = []
        noPU_array = []

        for ticket in old_tickets_sort:
            if re.match(with_PU, ticket['_id']):
                if re.match(with_noPU, ticket['_id']):
                    noPU_array.append(ticket)
                else:
                    PU_array.append(ticket)

        ######################################################################################
        for ticket in tickets_to_be_pushed:
            print('Creating a ticket for %s with ids %s' %(ticket['cmssw_release'], ticket['workflow_ids']))
        #Looping through all the new tickets that need to be pushed to server
            response = relval.put('tickets', ticket)
            inner_response = response['response']
            ticket_prepid = inner_response['prepid']
        #Putting the ticket on the server
            try:
            #Trying to create relvals
                print(ticket_prepid)
                response_relval = relval.create_relvals(ticket_prepid)

                print(response_relval)

                ticket_relvals = relval.get('relvals', query='ticket=' + ticket_prepid)

                for one_relval in ticket_relvals:
                    print('Pushing %s relval to next state' %one_relval['prepid'])
                    if one_relval['status'] == 'new':
                        relval.next_status(one_relval['prepid'])
                        relval.next_status(one_relval['prepid'])
                    #The relval status should be changed from new to submitting,
                    #which is two steps ahead of new
            except:
                print('It is not possible to either create relvals or push the status from new to submitting')


def create_relmon():
    relmon = Relmon()
    new_relmon = {}
    make_relmon = relmon.create(new_relmon)

new_releases(releases)
relvals_creation(new)
#create_relmon()                                    