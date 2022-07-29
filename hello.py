"""
Program for automatisation of creating tickets and RelVals
"""
from __future__ import print_function
import time
#from platform import release
import xml.etree.ElementTree as ET
import os
import re
import sys
#import json
import requests
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

RELEASES = get_releases()
NEW = []
OLD = []
GT_STRING_ARR = []
GT_STRING = ""
PU_TO_BE_PUSHED = []
PU = []
FULLSIM_PU = []
FULLSIM_PU_TO_BE_PUSHED = []
#NEW_TICKETS = []
NO_RECO_PU = []
RECO_PU = []
noPU = []

def new_releases(releases):
    """
    This function checks for new releases that follow the PATTERN,
    checks the existance of old.txt file, puts new releases into
    new[] and new.txt and also updates old.txt file
    """
    global OLD
    global NEW
    #pattern = 'CMSSW(_\d{1,2}){2}_0(_pre([2-9]|(\d{2,10})))?$'
    #The regex for catching all the first releases and pres
    pattern = r'CMSSW(_\d{1,2}){2}_0(_pre([2-9]|(\d{2,10})))+$'
    #The regex for fetching all the pres
    releases = [x for x in releases if re.match(pattern, x[1])]
    #This is taking away all the releases that don't match the regex


    if not os.path.exists('old.txt'):
        with open('old.txt', 'w') as output_file:
            for rel in releases:
                if re.match(pattern, rel[1]):
                    output_file.write(rel[1] + '\n')
        sys.exit(0)
    #If there exists no OLD.TXT file

    old_str = open('old.txt', 'r')

    OLD = old_str.read().split('\n')
    OLD.remove('')
    old_sorted = []
    old_sorted = sorted(OLD, key=lambda x: tuple(int(i) for i in re.findall(r'\d+', x)))
    #Sorting old releases. x is a string, example: x="CMSSW_12_1_0_pre3" and
    #list is sorted by numbers from left to right
    OLD = old_sorted
    for rel in releases:
        if rel[1] not in OLD:
            NEW.append(rel)
            #appending new releases to the list new[]
            ### Sljedeca linija je iskljucivo zbog probe
            #new.append(releases[-1])


    with open('new.txt', 'w') as output_file:
        for new_rel in NEW:
            output_file.write(new_rel[1] + '\n')          #Putting new releases into file

    with open('old.txt', 'w') as input_file:
        for rel in releases:
            input_file.write(rel[1] + '\n')           #Updating old releases for next iteration

def relvals_creation(new):
    """
    This function creates tickets and RelVals. Argument new is array of new releases
    """
    if len(new) == 0:       #If the new releases list is empty then there are no new releases
        print('There are no new releases')
        sys.exit(1)
    else:
        #Otherwise, we will need a relval class
        relval = RelVal()

        old_tickets = relval.get('tickets', query='cmssw_release=' + OLD[-1])
        #old_tickets = relval.get('tickets', query='cmssw_release=CMSSW_12_0_0_pre*')
        #This line gets all old tickets with specified query
        old_tickets_sort = sorted(old_tickets, key=lambda x: tuple(int(i) for i in  x['_id'].split('pre')[1].split('__')[0]))
        print(len(old_tickets_sort))
        tickets_to_be_pushed = []
        #REGEX FOR TICKETS WITHOUT noPU                           ^((?!noPU).)*$
        #REGEX FOR TICKETS WITH noPU                               .*(noPU)+.*$
        for old_ticket in old_tickets_sort:
            ticket = old_ticket
            ticket['cmssw_release'] = new[0][1]
            ticket['batch_name'] = old_ticket['batch_name'] + '_AUTO_CREATION'
            tickets_to_be_pushed.append(ticket)
        #New tickets have the same values besides 'cmssw_release'

        for ticket in tickets_to_be_pushed:
            print('Make ticket for %s' %(ticket['cmssw_release']))
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
                    else:
                        print("Status is not new")
                    #The relval status should be changed from new to submitting,
                    #which is two steps ahead of new
            except KeyboardInterrupt as key_inter:
                print('The execution of the program was interrupted by keyboard interrupt: ')
                print(key_inter)
                #sys.exit(2)
            except:
                print('It is not possible to create relvals or push the status to submitting')

def nopu_full_creation(new):
    """
    This function creates noPU tickets and RelVals. Argument new is array of new releases
    """
    global GT_STRING_ARR
    global PU
    global GT_STRING
    global noPU
    if len(new) == 0:       #If the new releases list is empty then there are no new releases
        print('There are no new releases')
        sys.exit(1)
    else:
        #Otherwise, we will need a relval class
        relval = RelVal()

        old_tickets = relval.get('tickets', query='cmssw_release=' + OLD[-1])
        #This line gets all old tickets with specified query
        old_tickets_sort = sorted(old_tickets, key=lambda x: tuple(int(i) for i in  x['_id'].split('pre')[1].split('__')[0]))

        #REGEX FOR TICKETS WITHOUT noPU                           ^((?!noPU).)*$
        #REGEX FOR TICKETS WITH noPU                               .*(noPU)+.*$
        with_noPU = ".*(noPU)+.*$"
        with_PU = ".*(PU)+.*$"


        for old_ticket in old_tickets_sort:
            if re.match(with_noPU, old_ticket['_id']):
                ticket = old_ticket
                ticket['cmssw_release'] = new[0][1]
                ticket['batch_name'] = old_ticket['batch_name'] + '_AAA'
                noPU.append(ticket)
            elif re.match(with_PU, old_ticket['_id']):
                ticket = old_ticket
                ticket['cmssw_release'] = new[0][1]
                ticket['batch_name'] = old_ticket['batch_name'] + '_AAA'
                PU.append(ticket)
        #This for loop makes noPU and PU arrays
        #New tickets have the same values besides 'cmssw_release'

        # for ticket in noPU:
        #     print('Make noPU ticket for %s' %(ticket['cmssw_release']))
        #     print(ticket)
        # #Looping through all the new tickets that need to be pushed to server
        #     if not re.match('.*(RECO)+.*$', ticket['batch_name']):
        #         response = relval.put('tickets', ticket)
        #         inner_response = response['response']
        #         ticket_prepid = inner_response['prepid']
        #Putting the ticket on the server##########################################################################
            # try:
            # #Trying to create relvals
            #     print(ticket_prepid)
            #     response_relval = relval.create_relvals(ticket_prepid)

            #     print(response_relval)

            #     #ticket_relvals = relval.get('relvals', query='ticket=CMSSW_12_5_0_pre3__UPSG_Std*')
            #     ticket_relvals = relval.get('relvals', query='ticket=' + ticket_prepid)
            #     #print(*ticket_relvals, sep = "\n \n")

            #     for one_relval in ticket_relvals:
            #         print('Pushing %s relval to next state' %one_relval['prepid'])
            #         if one_relval['status'] == 'new':
            #             relval.next_status(one_relval['prepid'])
            #             print("Status pushed once")
            #             relval.next_status(one_relval['prepid'])
            #             print("Status pushed twice")
            #         else:
            #             print("Status is not new")
            #         #The relval status should be changed from new to submitting,
            #         #which is two steps ahead of new
            
            #     #time.sleep(3*60*60)

            #     #all_sub = 0
            #     #Making sure all statuses are submitted or done, for the output datasets.

            #     # while all_sub == 0:
            #     #     all_sub = 1
            #     #     print("Checking if all statuses are pushed properly")
            #     #     #If it comes across a relval's status not pushed enough times, it pushes it again.
            #     #     #After that program's execution is postponed by 1 hour.
            #     #     for rel in ticket_relvals:
            #     #         if rel['status'] != 'submitting' and rel['status'] != 'done' and rel['status'] != 'submitted':
            #     #             if rel['status'] == 'new':
            #     #                 rel.next_status(rel['prepid'])
            #     #                 rel.next_status(rel['prepid'])
            #     #             elif rel['status'] == 'approved':
            #     #                 rel.next_status(rel['prepid'])
            #     #             all_sub = 0
            #     #             print("Statuses not pushed properly")
            #     #     if all_sub == 0:
            #     #         print("Waiting for the statuses to complete.")
            #     #         time.sleep(15)
            #     # print("Something")

            #     # while GT_STRING == "":
            #     #     for rel in ticket_relvals:
            #     #         if rel['status'] == 'submitted'  or rel['status'] == 'done':
            #     #             if rel['output_datasets'].split('/')[-1] == "GEN-SIM-RECO":
            #     #                 GT_STRING = rel['output_datasets'].split('/')[2]
            #     #     if GT_STRING == "":
            #     #         time.sleep(3*60*60)
            #     #         #Pause it for 3 hours
            #     # GT_STRING = GT_STRING + "_____" + ticket['batch_name'].split('_')[1]
            #     # GT_STRING_ARR.append(GT_STRING)
            #     # GT_STRING = ""
            # except KeyboardInterrupt as key_inter:
            #     print('The execution of the program was interrupted by keyboard interrupt: ')
            #     print(key_inter)
            #     #sys.exit(2)
            # except:
            #     print("Can't create relvals, push the status to submitting or take GT String!")

def nopu_reco_only_creation(new):
    """
    This function creates noPU tickets and RelVals. Argument new is array of new releases
    """
    global GT_STRING_ARR
    global PU
    global GT_STRING
    global noPU
    if len(new) == 0:       #If the new releases list is empty then there are no new releases
        print('There are no new releases')
        sys.exit(1)
    else:
        print('There is a new release!')
        #Otherwise, we will need a relval class
        relval = RelVal()
        local_gt_string = "CMSSW_12_5_0_pre3-124X_mcRun3_2022_realistic_v8-v2"

        print("Ovo je noPU niz: ")
        print(len(noPU))
        output_datasets = []
        for ticket in noPU:
            print("Something")
            if re.match(".*(RECO)+.*$", ticket['batch_name']):
                print('Make noPU RECO ticket for %s' %(ticket['cmssw_release']))
                print(ticket)
                relvals_of_ticket = relval.get('relvals', query='ticket=' + ticket['prepid'])
                #print("Ovo je prepid" + ticket['prepid'].split('__AUTOMATED')[0] + ticket['prepid'].split('__AUTOMATED')[1])

                for rel in relvals_of_ticket:
                    print("In the GT string extraction for loop")
                    
                    output_datasets.append(rel['output_datasets'])
                    print(output_datasets)

                    for output in output_datasets:
                        print("Output jedan")
                        print(output)
                        if len(output) > 0 and output[0].split('/')[-1] == "GEN-SIM-RECO":
                            local_gt_string = output.split('/')[2]
                            print("Ovo je lokalni gt string")#################################################
                            print(type(local_gt_string))
                            break
                #Looping through all the new tickets that need to be pushed to server
                #Relvals have output_datasets, not tickets!

                ticket['rewrite_gt_string'] = local_gt_string
                print()
                print(ticket)
                print()
                response = relval.put('tickets', ticket)
                inner_response = response['response']
                ticket_prepid = inner_response['prepid']
                #Putting the ticket on the server
                try:
                #Trying to create relvals
                    print(ticket_prepid)
                    response_relval = relval.create_relvals(ticket_prepid)

                    print(response_relval)

                    #ticket_relvals = relval.get('relvals', query='ticket=CMSSW_12_5_0_pre3__UPSG_Std*')
                    ticket_relvals = relval.get('relvals', query='ticket=' + ticket_prepid)
                    #print(*ticket_relvals, sep = "\n \n")

                    for one_relval in ticket_relvals:
                        print('Pushing %s relval to next state' %one_relval['prepid'])
                        if one_relval['status'] == 'new':
                            relval.next_status(one_relval['prepid'])
                            print("Status pushed once")
                            relval.next_status(one_relval['prepid'])
                            print("Status pushed twice")
                        else:
                            print("Status is not new")
                        #The relval status should be changed from new to submitting,
                        #which is two steps ahead of new
                
                    #time.sleep(3*60*60)

                except KeyboardInterrupt as key_inter:
                    print('The execution of the program was interrupted by keyboard interrupt: ')
                    print(key_inter)
                    #sys.exit(2)
                except:
                    print("Can't create relvals, push the status to submitting or take GT String!")

def pu_creation(pu):
    """
    This function creates PU tickets and RelVals. Argument pu is array of PU tickets.
    Each ticket's output_datasets need to be changed to GT_STRING
    """
    global NEW
    global GT_STRING
    global PU_TO_BE_PUSHED
    if len(pu) == 0:       #If the new releases list does not contain PU tickets then we are done
        print('There are no new PU tickets to be created.')
        sys.exit(1)
    else:
        #Otherwise, we will need a relval class
        relval = RelVal()
        
        for old_ticket in pu:
            ticket = old_ticket
            ticket['output_datasets'] = GT_STRING
            ticket['cmssw_release'] = NEW[0][1]
            PU_TO_BE_PUSHED.append(ticket)
        #This for loop modifies ticket's output_datasets and appends it for pushing to server

        for ticket in PU_TO_BE_PUSHED:
            print('Make PU ticket for %s' %(ticket['cmssw_release']))
        #Looping through all the PU tickets that need to be pushed to server
            response = relval.put('tickets', ticket)
            inner_response = response['response']
            #GT_STRING = inner_response
            ticket_prepid = inner_response['prepid']
        #Putting the ticket on the server
            try:
            #Trying to create relvals
                print(ticket_prepid)
                #response_relval = relval.create_relvals(ticket_prepid)

                #print(response_relval)

                ticket_relvals = relval.get('relvals', query='ticket=CMSSW_12_5_0_pre3__UPSG_Std*') #TESTING
                #ticket_relvals = relval.get('relvals', query='ticket=' + ticket_prepid)
                print(*ticket_relvals, sep = "\n \n")

                for one_relval in ticket_relvals:
                    print('Pushing %s relval to next state' %one_relval['prepid'])
                    if one_relval['status'] == 'new':
                        relval.next_status(one_relval['prepid'])
                        relval.next_status(one_relval['prepid'])
                    else:
                        print("Status is not new")
                    #The relval status should be changed from new to submitting,
                    #which is two steps ahead of new
            
                time.sleep(3*60*60)
                #Program's execution is postponed due to status updates
                all_sub = 0
                #Making sure all statuses are submitted or done, for the output datasets to be created.

                while all_sub == 0:
                    all_sub = 1
                    #If it comes across a relval's status not pushed enough times, it pushes it again.
                    #After that program's execution is postponed by 1 hour.
                    for rel in ticket_relvals:
                        if rel['status'] != 'submitting' and rel['status'] != 'done':
                            if rel['status'] == 'new':
                                rel.next_status(rel['prepid'])
                                rel.next_status(rel['prepid'])
                            else:
                                rel.next_status(rel['prepid'])
                            all_sub = 0
                    if all_sub == 0:
                        time.sleep(60*60)
            except KeyboardInterrupt as key_inter:
                print('The execution of the program was interrupted by keyboard interrupt: ')
                print(key_inter)
                #sys.exit(2)
            except:
                print("Can't create relvals, push the status to submitting or take GT String!")

def create_relmon():
    """
    Function for creating relmon
    """
    relmon = Relmon()
    new_relmon = {}
    make_relmon = relmon.create(new_relmon)

def pu_full_creation(pu, type):
    """
    The function to create PU tickets. Arguments are list of PU tickets and type. Type is a string
    which should be either 'fullsim', 'UPSG' or 'HIN'
    """
    if type != 'fullsim' and type != 'UPSG' and type != 'HIN':
        print('Type should be either fullsim, UPSG or HIN. Wrong type entered.')
    else:
        global NEW
        global NO_RECO_PU

        #We want to access global variable NO_RECO_PU
        for ticket in pu:
            print("Ticket with the batch name:" + ticket['batch_name'] + "is being operated with")
            batch_name = ticket['batch_name'].split('_')[1]
            print("Ovo je dio za provjeru" + batch_name)
            if batch_name == type and not ticket['batch_name'].split('_')[-2].startswith('RECO'):
                ############################################Privremeno
                print("This ticket's batch name does not contain RECO")
                ticket['cmssw_release'] = NEW[0][1]
                NO_RECO_PU.append(ticket)
                #For now it should find just one, because we merged the similar tickets
            relval = RelVal()
            # print("Printanje Novog")
            # print(NEW[0][1])
            nopu_tickets = relval.get('tickets', query='cmssw_release=' + NEW[0][1] + "*")
            print("nopu duzina kuuurca")
            print(len(nopu_tickets))
            print()
            #Since we need the noPU tickets before we work out PU tickets, the name is fine
            for nopu_ticket in nopu_tickets:
                print("Searching for noPU ticket to match with PU one.")
                print(nopu_ticket['batch_name'])
                print()
                if nopu_ticket['batch_name'].split('_')[1] == type:
                    print("We have found the ticket with proper batch name")
                    i = 0
                    for gt_string in GT_STRING_ARR:
                        print("Looking for a matching gt string with this one: " + gt_string)
                        if i == 1:
                            print("We already found the matching gt string")
                        if gt_string.split('_____')[1].startswith(type) and i == 0:
                            print("Matching gt string found")
                            ticket['rewrite_gt_string'] = gt_string
                            i = 1
                            break

            #We have created fullsim PU ticket that now can be pushed
            print("Ovo je lista NO_RECO_KURCEVA")
            print(len(NO_RECO_PU))

            #time.sleep(3*60*60)
        print("Ovo su NO_RECO_PU tiketi: ")
        for ticket in NO_RECO_PU:
            print(ticket['batch_name'])
        print()
        print()
        print()




        for ticket in NO_RECO_PU:
            print('Make ticket for %s of the type' %(ticket['cmssw_release']))
            print(type)
            print(len(NO_RECO_PU))
        #Looping through all the new tickets that need to be pushed to server
            response = relval.put('tickets', ticket)
            inner_response = response['response']
            ticket_prepid = inner_response['prepid']
        #Putting the ticket on the server
            print("Got to the try to create relvals part")
            try:
            #Trying to create relvals
                print(ticket_prepid)
                response_relval = relval.create_relvals(ticket_prepid)
                print("Relvals created")

                print(response_relval)
                ticket_relvals = relval.get('relvals', query='ticket=' + ticket_prepid)

                for one_relval in ticket_relvals:
                    print('Pushing %s relval to next state' %one_relval['prepid'])
                    if one_relval['status'] == 'new':
                        relval.next_status(one_relval['prepid'])
                        print("Status pushed once")
                        relval.next_status(one_relval['prepid'])
                        print("Status pushed twice")
                    else:
                        print("Status is not new")
                    #The relval status should be changed from new to submitting,
                    #which is two steps ahead of new
            
                #time.sleep(3*60*60)

                #all_sub = 0
                #Making sure all statuses are submitted or done, for the output datasets.
            except:
                print("Can't create relvals, push the status to submitting or take GT String!")

def pu_reco_only_creation(pu):
    global RECO_PU
    global NEW
    for ticket in pu:
        if ticket['batch_name'].split('_')[-1].startswith('RECO'):
            RECO_PU.append(ticket)
    #For now it should find just one, cause we merged the similar tickets
    relval = RelVal()

    # #We have created fullsim PU ticket that now can be pushed
    for ticket in RECO_PU:
        print('Make RECO ticket for %s' %(ticket['cmssw_release']))
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
                    print("Status pushed once")
                    relval.next_status(one_relval['prepid'])
                    print("Status pushed twice")
                else:
                    print("Status is not new")
                #The relval status should be changed from new to submitting,
                #which is two steps ahead of new
        
            time.sleep(3*60*60)
        except KeyboardInterrupt as key_inter:
            print('The execution of the program was interrupted by keyboard interrupt: ')
            print(key_inter)
            #sys.exit(2)
        except:
            print("Can't create relvals, push the status to submitting or take GT String!")



new_releases(RELEASES)
relval = RelVal()
#relvals_creation(NEW)
nopu_full_creation(NEW)

print(NEW)
old_tickets = relval.get('tickets', query='cmssw_release=' + OLD[-1])
print(len(old_tickets))
print(len(noPU))
print(len(PU))

nopu_tickets = relval.get('tickets', query='cmssw_release=' + NEW[0][1] + "*")

#old_tickets = relval.get('tickets', query='cmssw_release=' + old[-1])

GT_STRING_ARR = ['CMSSW_12_5_0_pre2-124X_mcRun3_2022_realistic_HI_v3-v1_____AUTOMATED_HIN_noPU2022_AUTO_CREATION',
                 'CMSSW_12_5_0_pre2-124X_mcRun3_2022_realistic_v3-v3_____AUTOMATED_fullsim_noPU_2022_14TeV_AUTO_CREATION',
                 'CMSSW_12_5_0_pre2-124X_mcRun4_realistic_v4_2026D88PU200_RECOonly-v1_____AUTOMATED_UPSG_Std_2026D88noPU_AUTO_CREATION']

nopu_full_creation(NEW)
print()
print()
print("Funkcija full nopu zavrsila rad")
print()
print()
nopu_reco_only_creation(NEW)
print()
print()
print("Funkcija nopu reco only zavrsila rad")
print()
print()
pu_full_creation(PU, 'HIN')
print()
print()
print("Funkcija pu HIN zavrsila rad")
print()
print()
pu_full_creation(PU, 'UPSG')
print()
print()
print("Funkcija pu UPSG zavrsila rad")
print()
print()
pu_full_creation(PU, 'fullsim')
print()
print()
print("Funkcija pu fullsim zavrsila rad")
print()
print()
pu_reco_only_creation(PU)









#pu_creation(PU)
# relmon = Relmon()
# print(relval.__dict__)
# print()
# print(relmon.__dict__)
# print()
# print(relmon.get('tickets', "",query='*'))
# print(relmon)
#no_reco_pu_creation(PU, 'fullsim')



# proba = "/nestonesto/"
# print(proba.split('/'))


#print(*old_tickets[2], sep = "\n")
#print(old_tickets[0])