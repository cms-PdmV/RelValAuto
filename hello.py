"""
Document for blah
"""
import xml.etree.ElementTree as ET
import requests
import os
import re
import sys
import json
from relval import RelVal

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

def new_releases(releases):
    """
    This function checks for new releases that follow the PATTERN, checks the existance of old.txt file,
    puts new releases into new[] and new.txt and also updates old.txt file
    """

    pattern = 'CMSSW(_\d{1,2}){2}_0(_pre([2-9]|(\d{2,10})))?$'

    releases = [x for x in releases if re.match(pattern, x[1])]

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
       
    for x in releases:
        if x[1] not in old:
            new.append(x)
    ### Sljedeca linija je iskljucivo zbog probe
    new.append(releases[-1])


    with open('new.txt', 'w') as output_file:
        for x in new:
            output_file.write(x[1] + '\n')

    with open('old.txt', 'w') as input_file:
        for x in releases:
            input_file.write(x[1] + '\n')    


def relvals_creation(new):
    
    if len(new) == 0:
        print('There are no new releases')
        sys.exit(1)
    else:

        relval = RelVal()
        tickets = relval.get('tickets', query='cmssw_release=*')

        ticket = {}

        ticket['cmssw_release'] = new[0][1]
        ticket['workflow_ids'] = tickets[-1]['workflow_ids']

        print('Creating a ticket for %s with ids %s' %(ticket['cmssw_release'], ticket['workflow_ids']))

        response = relval.put('tickets', ticket)

        inner_response = response['response']
        ticket_prepid = inner_response['prepid']
        
        try:
            print(ticket_prepid)
                
            response_relval = relval.create_relvals(ticket_prepid)

            print(response_relval)
            

            ticket_with_relvals = tickets[-1]
            ticket_prepid = ticket_with_relvals['prepid']

            ticket_relvals = relval.get('relvals', query='ticket=' + ticket_prepid)

            for one_relval in ticket_relvals:
                print('Pushing %s relval to next state' %one_relval['prepid'])
                if one_relval['status'] == 'new':
                    relval.next_status(one_relval['prepid'])
                    relval.next_status(one_relval['prepid'])
        except:
            print('It is not possible to either create relvals or push the status from new to submitting')

new_releases(releases)
relvals_creation(new)











