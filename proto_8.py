"""
Program for automatisation of creating tickets and RelVals. The program has specified functions for
creating noPU, PU, RECOonly tickets. The names of the functions are intuitive.
"""
from __future__ import print_function
import time
import xml.etree.ElementTree as ET
import os
import re
import sys
import json
import requests
import traceback
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
                    type = child2.get('type')
                    state = child2.get('state')
                    release = tuple((name, label, type, state))
                    arr.append(release)

    arr_sort = []
    arr_sort = sorted(arr, key=lambda x: tuple(int(i) for i in  x[1].split('_')[1:4]))
    return arr_sort

RELEASES = get_releases()
NEW = []
OLD = []
GT_STRING_ARR = []
PU_TO_BE_PUSHED = []
PU = []
FULLSIM_PU = []
FULLSIM_PU_TO_BE_PUSHED = []
FULL_PU = []
RECO_PU = []
noPU = []
FINISHED_NOPU = 0
FINISHED_PROCESS = 0

CHANGES_STR = []
with open('data.txt') as data:
    CHANGES_STR = data.read().split('\n')

CHANGES = []
print(len(CHANGES_STR))
if len(CHANGES_STR) > 1:
    for str in CHANGES_STR:
        if len(str) > 0:
            CHANGES.append(json.loads(str))

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

    with open('old.txt', 'r', encoding='utf-8') as old_str:
        OLD = old_str.read().split('\n')


    #old_str = open('old.txt', 'r')

    #OLD = old_str.read().split('\n')
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

    with open('new.txt', 'w') as output_file:
        for new_rel in NEW:
            output_file.write(new_rel[1] + '\n')          #Putting new releases into file
    return releases

def create_nopu_and_pu_arrays(new):
    #We will need a relval class
    
    print("\n\n\n\n\n ENTERED CREATE NOPU AND PU ARRAYS \n\n\n\n\n")
    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
        sbs.write("\n\n\n ENTERED CREATE NOPU AND PU ARRAYS (line 129)\n\n\n")

    relval = RelVal()
    global noPU
    global PU
    global step_by_step

    #old_tickets = relval.get('tickets', query='cmssw_release=' + OLD[-1])
    #old_tickets = relval.get('tickets', query='cmssw_release=CMSSW_12_5_0_pre4')
    old_tickets = []
    
    old_tickets = relval.get('tickets', query='cmssw_release=' + OLD[-1])
    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
        sbs.write("Old tickets fetched from the server. (line 142)\n")
        sbs.write("\n")

    old_tickets_sort = sorted(old_tickets, key=lambda x: tuple(int(i) for i in  x['_id'].split('pre')[1].split('__')[0])) ############################## COMMENTED OUT JUST FOR TESTING
    #old_tickets_sort = old_tickets


    with_noPU = ".*(noPU)+.*$"      #REGEX FOR TICKETS WITHOUT noPU
    with_PU = ".*(PU)+.*$"          #REGEX FOR TICKETS WITH noPU

    for old_ticket in old_tickets_sort:
        if re.match(with_noPU, old_ticket['_id']) and old_ticket['batch_name'].startswith("AUTOMATED"):
            ticket = old_ticket
            ticket['cmssw_release'] = new[0][1]
            #ticket['cmssw_release'] = "CMSSW_12_4_7" ######################### For testing
            print("Ticket with " + ticket['batch_name'] + " is put to the noPU array")
            with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                sbs.write("Ticket with " + ticket['batch_name'] + " is put to the noPU array (line 159)\n")

            noPU.append(ticket)
        elif re.match(with_PU, old_ticket['_id']) and old_ticket['batch_name'].startswith("AUTOMATED"):
            ticket = old_ticket
            ticket['cmssw_release'] = new[0][1]
            #ticket['cmssw_release'] = "CMSSW_12_4_7" ######################### For testing
            print("Ticket with " + ticket['batch_name'] + " is put to the PU array")
            with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                sbs.write("Ticket with " + ticket['batch_name'] + " is put to the PU array (line 168)\n")

            PU.append(ticket)
    #This for loop makes noPU and PU arrays
    #New tickets have the same values besides 'cmssw_release'

    print("noPU and PU arrays created\n\n")
    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
        sbs.write("noPU and PU arrays created (line 176)\n\n")
    print(len(noPU))
    print(len(PU))

def creating_relvals(ticket_prepid):
    """
    This function creates relvals for the given ticket prepid
    """
    print("\n\n\n\n\n ENTERED CREATING RELVALS \n\n\n\n\n")
    print(ticket_prepid)
    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
        sbs.write("\n\n\n ENTERED CREATING RELVALS (line 187)\n\n\n")

    relval = RelVal()
    print("Trying to create relvals for the ticket with prepid: " + ticket_prepid)
    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
        sbs.write("Trying to create relvals for the ticket with prepid: " + str(ticket_prepid))
        sbs.write(" (line 193)\n")

    response_relval = relval.create_relvals(ticket_prepid)

    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
        sbs.write("Ticket prepid for our relval_status_pushing.py is: " + ticket_prepid)
        sbs.write(" (line 199)\n")
    with open("relvals_for_pushing.txt", "w", encoding="utf-8") as relvals_for_pushing:
        relvals_for_pushing.write(ticket_prepid)

    time.sleep(1*60)

    with open('relval_status_pushing.py', 'r', encoding="utf-8") as relval_pushing_code:
        exec(relval_pushing_code.read())

    ticket_relvals = relval.get('relvals', query='ticket=' + ticket_prepid)
    return ticket_relvals

def gt_string_append(ticket_prepid, ticket_batch_name):
    """
    This function appends gt string for every ticket to the gt strings array. Besides gt string,
    it also adds batch name so we can match the correct noPU tickets with correct PU tickets.
    """
    global GT_STRING_ARR
    print("\n\n\n\n\n ENTERED GT STRING APPEND \n\n\n\n\n")
    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
        sbs.write("\n\n\n ENTERED GT STRING APPEND (line 219)\n\n\n")

    gt_str = ""
    
    while gt_str == "":
        ticket_relvals = relval.get('relvals', query='ticket=' + ticket_prepid)
        print("We are trying to check statuses of ticket " + ticket_batch_name)
        with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
            sbs.write("We are trying to check statuses of ticket " + ticket_batch_name)
            sbs.write(" (line 228)\n")

        for rel in ticket_relvals:
            if rel['status'] == 'submitted'  or rel['status'] == 'done':
                print("This is relval status: " + rel['status'])
                print("This ticket is either submitted or done")
                for dataset in rel['output_datasets']:
                    if dataset.split('/')[-1] == "GEN-SIM-RECO":
                        gt_str = dataset.split('/')[2]
                        print("We have found GT string.")
                        with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                            sbs.write("We have found the GT string. (line 239)\n")
                        break
                print("After if relval status: " + rel['status'] + " and gt string " + gt_str)
            if not gt_str == "":
                break
        if gt_str == "":
            print("This should not happen, stop program manually!!!")
            with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                sbs.write("This should not happen, stop program manually!!! (LINE 247)\n")
            time.sleep(3*60)
    gt_str = gt_str + "_____" + ticket_batch_name.split('_')[1]
    print("GT String for this ticket is: " + gt_str)
    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
        sbs.write("GT string for this ticket is: " + gt_str)
        sbs.write(" (line 253)\n")
    GT_STRING_ARR.append(gt_str)

def nopu_full_creation(new):
    """
    This function creates noPU tickets and RelVals. Argument new is array of new releases
    """
    print("\n\n\n\n\n ENTERED NOPU FULL CREATION (line 260)\n\n\n\n\n")
    global GT_STRING_ARR
    global PU
    global noPU
    if len(new) == 0:       #If the new releases list is empty then there are no new releases
        print('There are no new releases.')
        with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
            sbs.write("There are no new releases. (line 267)\n")
        sys.exit(1)
    else:
        #Otherwise, we will need a relval class
        if len(noPU) > 0:
            ticket_batch_and_prepids = []
            for ticket in noPU:
                ticket_prepid = ""
                #Looping through all the new tickets that need to be pushed to server
                print("Make noPU ticket for %s\n" %(ticket['batch_name']))
                with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                    sbs.write("Make noPU ticket for %s\n" %(ticket['batch_name']))
                    sbs.write(" (line 279)\n")

                already_made_nopu_tickets_batch_names = []
                with open('nopu.txt', 'r') as nopu_made_tickets:
                    already_made_nopu_tickets_batch_names = nopu_made_tickets.read().split('\n')

                print("\n\n\n\n\n")
                if (not re.match('.*(RECO)+.*$', ticket['batch_name'])) and  not (ticket['batch_name'] in already_made_nopu_tickets_batch_names):
                    ticket = change_properties(ticket)
                    print("Ovaj ticket nije ranije kreiran: ", ticket['batch_name'])
                    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                        sbs.write("This ticket is not made before (not in the .txt file) " + ticket['batch_name'])
                        sbs.write(" (line 291)\n")

                    response = relval.put('tickets', ticket)
                    inner_response = response['response']
                    ticket_prepid = inner_response['prepid']
                    with open('nopu.txt', 'a') as nopu_made_tickets:
                        nopu_made_tickets.write(inner_response['batch_name'] + "\n")

                    prepid_and_batch_name = ticket_prepid + "_____" + ticket['batch_name']
                    ticket_batch_and_prepids.append(str(prepid_and_batch_name))
            #Putting the ticket on the server##########################################################################
                try:
                #Trying to create relvals
                    print("Try to create relvals for noPU ticket with prepid: " + ticket_prepid)
                    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                        sbs.write("Try to create relvals for noPU ticket with prepid: " + ticket_prepid)
                        sbs.write(" (line 307)\n")
                    print("Ovo je raspali prepid: " + ticket_prepid)
                    creating_relvals(ticket_prepid) ################ COMMENTED OUT JUST FOR testing
                except KeyboardInterrupt as key_inter:
                    print("The execution of the program was interrupted by keyboard interrupt: \n")
                    print(key_inter)
                    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                        sbs.write("The execution of the program was interrupted by keyboard interrupt: \n")
                        sbs.write(key_inter)
                        sbs.write(" (line 316)\n")
                    #sys.exit(2)
                except Exception as e:
                    print(e)
                    print("Can't create relvals, push the status to submitting or take GT String!\n")
                    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                        sbs.write("This is the error: ")
                        sbs.write(e)
                        sbs.write(" (line 324)\n")

            print("Waiting for statuses to be pushed far enough.")
            with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                sbs.write("Waiting for statuses to be pushed far enough. (line 328)\n")
            
def nopu_reco_only_creation(new):
    """
    This function creates noPU tickets and RelVals. Argument new is array of new releases
    """
    print("\n\n\n\n\n ENTERED NOPU RECO CREATION \n\n\n\n\n")
    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
        sbs.write("\n\n\n ENTERED NOPU RECO CREATION (line 336) \n\n\n")
    global GT_STRING_ARR
    global PU
    global noPU
    ticket_prepid = ""
    if len(new) == 0:       #If the new releases list is empty then there are no new releases
        print('There are no new releases.')
        with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
            sbs.write("There are no new releases. (line 344)\n")
        sys.exit(1)
    else:
        #Otherwise, we will need a relval class
        relval = RelVal()
        already_made_nopu_tickets_batch_names = []
        with open('nopu.txt', 'r') as already_made_nopu:
            already_made_nopu_tickets_batch_names = already_made_nopu.read().split('\n')
        local_gt_string = ""
        output_datasets = []

        if len(noPU) > 0:
            for ticket in noPU:
                if re.match(".*(RECO)+.*$", ticket['batch_name']) and not (ticket['batch_name'] in already_made_nopu_tickets_batch_names):
                    print('Make noPU RECO ticket for %s' %(ticket['batch_name']))
                    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                        sbs.write("Make noPU ticket for %s (line 360)\n" %(ticket['batch_name']))
                        sbs.write("\n")
                    relvals_of_ticket = relval.get('relvals', query='ticket=' + ticket['prepid'])

                    for rel in relvals_of_ticket:
                        output_datasets.append(rel['output_datasets'])

                    for outputs in output_datasets:
                        for output in outputs:
                            if len(output) > 0 and output[0].split('/')[-1] == "GEN-SIM-RECO":
                                local_gt_string = output.split('/')[2]
                                break
                    #Looping through all the new tickets that need to be pushed to server
                    #Relvals have output_datasets, not tickets!

                    ticket['rewrite_gt_string'] = local_gt_string
                    #ticket = change_properties(ticket)
                    print(ticket)
                    response = relval.put('tickets', ticket)
                    inner_response = response['response']
                    print("Unutrasnji response: ")
                    print(inner_response)
                    with open('nopu.txt', 'a') as nopu_made_tickets:
                        nopu_made_tickets.write(inner_response['batch_name'] + "\n")
                        
                    ticket_prepid = inner_response['prepid']
                    #Putting the ticket on the server
                    try:
                        print("Trying to create relvals: \n\n\n")
                        with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                            sbs.write("Trying to create relvals. (line 390)\n")

                        #Trying to create relvals
                        creating_relvals(ticket_prepid)

                    except KeyboardInterrupt as key_inter:
                        print('The execution of the program was interrupted by keyboard interrupt: ')
                        with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                            sbs.write("The execution of the program was interrupted by keyboard interrupt: \n")
                            sbs.write(key_inter)
                            sbs.write(" (line 400)\n")
                        print(key_inter)
                        #sys.exit(2)
                    except Exception as e:
                        print("Can't create relvals, push the status to submitting or take GT String!")
                        print(e)
                        with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                            sbs.write("Can't create relvals, push the status to submitting or take GT String!")
                            sbs.write(e)
                            sbs.write(" (line 409)\n")
                else:
                    print("This is not a proper ticket")
        else:
            print("The noPU array is empty!")
            with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                sbs.write("The noPU array is empty! (line 415)\n")

def pu_full_creation(pu, type):
    """
    The function to create PU tickets. Arguments are list of PU tickets and type. Type is a string
    which should be either 'fullsim', 'UPSG' or 'HIN'
    """
    print("\n\n\n\n\n ENTERED PU FULL CREATION \n\n\n\n\n")
    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
        sbs.write("all_runs_step")

    relval = RelVal()
    if not type == 'fullsim' and not type == 'UPSG' and not type == 'HIN':
        print('Type should be either fullsim, UPSG or HIN. Wrong type entered.')
        with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
            sbs.write("Type should be either fullsim, UPSG or HIN. Wrong type entered (line 430)\n")
    else:
        global NEW
        FULL_PU = []
        #We want to access global variables NEW and FULL_PU
        if len(pu) > 0:
            already_made_pu_tickets_batch_names = []
            with open('pu.txt', 'r') as already_made_pu:
                already_made_pu_tickets_batch_names = already_made_pu.read().split('\n')

            for ticket in pu:
                print("Ticket with the batch name:" + ticket['batch_name'] + "is being operated with")

                batch_name = ticket['batch_name'].split('_')[1]
                if batch_name == type and not re.match('.*(RECO)+.*$', ticket['batch_name']) and not (ticket['batch_name'] in already_made_pu_tickets_batch_names):
                    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                        sbs.write("The batch_name of the ticket that is going to be operated with is: " + ticket['batch_name'])
                        sbs.write(" (line 447)\n")
                    #ticket['cmssw_release'] = NEW[0][1] ################################### For testing
                    
                    #For now it should find just one, because we merged the similar tickets
                    #nopu_tickets = relval.get('tickets', query='cmssw_release=' + NEW[0][1] + "*")

                    #Since we need the noPU tickets before we work out PU tickets, the name is fine
                    # for nopu_ticket in nopu_tickets:
                    #     if nopu_ticket['batch_name'].split('_')[1] == type:
                    #         print("We have found the ticket with proper batch name to match with our ticket!")
                    #         i = 0
                    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                        sbs.write("Searching for a proper GT string for our ticket. (line 459)\n")
                    for gt_string in GT_STRING_ARR:
                        #print("Looking for a matching gt string with this one: " + gt_string)
                        if gt_string.split('_____')[1].startswith(type):
                            print("Matching gt string found.")
                            with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                                sbs.write("Matching GT string found. (line 465)\n")
                                sbs.write(ticket['batch_name'] + "AND" + gt_string)
                                sbs.write("\n")
                            print(ticket['batch_name'] + " AND " + gt_string)

                            ticket['rewrite_gt_string'] = gt_string.split('_____')[0]
                            break
                    FULL_PU.append(ticket)
                #We have created fullsim PU ticket that now can be pushed
        else:
            print("The tickets of type PU do not exist.")
        if len(FULL_PU) > 0:        
            for ticket in FULL_PU:
            #Looping through all the new tickets that need to be pushed to server
                print('Make ticket for %s of the type' %(ticket['batch_name']))
                with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                    sbs.write("Make ticket for %s of the type" %(ticket['batch_name']))
                    sbs.write(" (line 482)\n")

                #ticket = change_properties(ticket)
                response = relval.put('tickets', ticket)
                inner_response = response['response']
                ticket_prepid = inner_response['prepid']
            #Putting the ticket on the server
                print("Try to create relvals: ")
                with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                    sbs.write("Try to create relvals (line 491)\n")
                try:
                    ticket_relvals = creating_relvals(ticket_prepid)
                except Exception as e:
                    print("Can't create relvals, push the status to submitting")
                    print(e)
                    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                        sbs.write("Can't create relvals, push the status to submitting or take GT String! (line 498)")
                        sbs.write(e)
                        sbs.write("\n")
                with open('pu.txt', 'a') as already_made_pu:
                    already_made_pu.write(ticket['batch_name'] + "\n")
        else:
            print("Tickets of type PU FULL do not exist.\n")
            with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                sbs.write("Tickets of type PU FULL do not exist.")
                sbs.write(" (line 507)\n")
    FULL_PU = []

def pu_reco_only_creation(pu):
    #global RECO_PU
    print("\n\n\n\n\n ENTERED PU RECO ONLY \n\n\n\n\n")
    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
        sbs.write("\n\n\n ENTERED PU RECO ONLY (line 514)\n\n\n")
    global NEW
    RECO_PU = []
    if len(pu) > 0:
        already_made_pu_tickets_batch_names = []
        with open('pu.txt', 'r') as already_made_pu:
            already_made_pu_tickets_batch_names = already_made_pu.read().split('\n')
        for ticket in pu:
            batch_name = ticket['batch_name']
            if re.match('.*(RECO)+.*$', batch_name) and not (ticket['batch_name'] in already_made_pu_tickets_batch_names):
                RECO_PU.append(ticket)
        #For now it should find just one, because we merged the similar tickets
        relval = RelVal()
    else:
        print("The tickets of type PU do not exist.")

    #We have created fullsim PU ticket that now can be pushed
    if len(RECO_PU) > 0:
        for ticket in RECO_PU:
            print('Make RECO ticket for %s' %(ticket['batch_name']))
            with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                sbs.write("Make RECO ticket for %s (line 535)" %(ticket['batch_name']))
                sbs.write("\n")
        #Looping through all the new tickets that need to be pushed to server
            response = relval.put('tickets', ticket)
            with open('pu.txt', 'a') as already_made_pu:
                already_made_pu.write(ticket['batch_name'] + "\n")
            inner_response = response['response']
            ticket_prepid = inner_response['prepid']
        #Putting the ticket on the server
            try:
                ticket_relvals = creating_relvals(ticket_prepid)
            except KeyboardInterrupt as key_inter:
                print('The execution of the program was interrupted by keyboard interrupt: ')
                print(key_inter)
                with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                    sbs.write("The execution of the program was interrupted by keyboard interrupt: \n")
                    sbs.write(e)
                    sbs.write(" (line 552)\n")
                sys.exit(2)
            except Exception as e:
                print("Can't create relvals, push the status to submitting or take GT String!")
                print(e)
                with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                    sbs.write("Can't create relvals, push the status to submitting or take GT String! (line 558)\n")
                    sbs.write(e)
                    sbs.write("\n")
    else:
        print("The tickets of type PU RECOonly do not exist.")
        with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
            sbs.write("The tickets of type PU RECOonly do not exist. (line 564)\n")
def create_relmon():
    """
    Function for creating relmon
    """
    relmon = Relmon()
    new_relmon = {}
    make_relmon = relmon.create(new_relmon)          

def change_properties(ticket):
    """
    Reading the html form and making changes to the ticket given as argument.
    """
    global CHANGES
    #All the changes loaded from the file
    for change in CHANGES:
        if change['batch_name'] == ticket['batch_name']:
            #If we have the correct batch name, we make changes
            with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                sbs.write("Changing a property of a ticket with batch_name: " + change['batch_name'])
                sbs.write(" (line 584)\n")
            print("Changing a property of a ticket with batch_name" + change['batch_name'])
            for property in change:
                if not change[property] == "":
                    #If we changed some property in the form
                    #It should be changed in the ticket
                    if property == "workflow_ids_add":
                        wfs_add = change[property].split("\n")
                        for wf in wfs_add:
                            ticket['workflow_ids'].append(float(wf))
                    elif property == "workflow_ids_remove":
                        wfs_rem = change[property].split("\n")
                        for wf in wfs_rem:
                            if float(wf) in ticket['workflow_ids']:
                                ticket['workflow_ids'].remove(float(wf))
                    elif not property == "cmssw_release":
                        ticket[property] = change[property]
    return ticket

def check_nopu_relvals_status(cmssw_release):
    print("\n\n\n\n\n ENTERED CHECK NOPU RELVALS STATUS \n\n\n\n\n")
    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
        sbs.write("\n\n\n\ ENTERED CHECK NOPU RELVALS STATUS (line 606)\n\n\n")
    relval = RelVal()
    check_status = 1
    nopu_arr = relval.get('tickets', query='cmssw_release=' + cmssw_release)
    #nopu_arr = relval.get('tickets', query='cmssw_release=CMSSW_12_4_6')
    print("Working with this version for testing")

    print(len(nopu_arr))

    for ticket in nopu_arr:
        if not re.match('.*(RECO)+.*$', ticket['batch_name']) and re.match('.*(noPU)+.*$', ticket['batch_name']) and not re.match('.*(fullsim)+.*$', ticket['batch_name']) :#FOR TESTING
            print("Since the noPU tickets are made, to continue with PU tickets, all relvals' statuses must be done.")
            print("This ticket's prepid is: ", ticket['prepid'])
            with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                sbs.write("Since the noPU tickets are made, to continue with PU tickets, all relvals' statuses must be 'done'\n")
                sbs.write("This ticket's prepid is: ", ticket['prepid'])
                sbs.write(" (line 623)\n")
            if not re.match('.*(RECO)+.*$', ticket['batch_name']):
                #check_status = 0
                relval = RelVal()
                ticket_prepid = ticket['prepid']

                ticket_relvals = relval.get('relvals', query='ticket=' + ticket_prepid)

                for rel in ticket_relvals:
                    print(rel['prepid'])
                    print(rel['status'])
                    if not rel['status'] == "done":
                        check_status = 0
                        print("The status of this relval is not done. The program will make a pause. Duration: 6 hours")
                        with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                            sbs.write("The status of this relval is not done. The program will be stopped for 6 hours. (line 638)\n")
                        return check_status
            else:
                print("RECO ticket skipped.")
    return check_status

def gt_arr_creation(new):
    print("\n\n\n\n\n ENTERED GT STRING ARRAY CREATION \n\n\n\n\n")
    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
        sbs.write("\n\n\n ENTERED GT STRING ARRAY CREATION (line 647)\n\n\n")
    relval = RelVal()
    global GT_STRING_ARR

    #nopu_arr = relval.get('tickets', query='cmssw_release=CMSSW_12_4_6')
    nopu_arr = relval.get('tickets', query='cmssw_release=' + new[0][1]) ################################### Real one, upper one is just for testing

    for ticket in nopu_arr:
        if not re.match('.*(RECO)+.*$', ticket['batch_name']) and re.match('.*(noPU)+.*$', ticket['batch_name']):
            gt_string_append(ticket['prepid'], ticket['batch_name'])

print("The program is being executed on the date: ")
seconds = time.time()
print(time.ctime(seconds))
with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
    sbs.write("The program is being executed on the date: ")
    sbs.write(time.ctime(seconds))
    sbs.write("\n")
    sbs.write("\nThese are the results: \n")
print("\nThese are the results: \n")

releases = new_releases(RELEASES)
relval = RelVal()

create_nopu_and_pu_arrays(NEW)
print()
print()
print("The noPU and PU arrays are created.")
print()
print()
with open("checkpoint.txt", "r+") as checkpoint_file:
    if checkpoint_file.read() == "":
        nopu_full_creation(NEW)
        print()
        print()
        print("Function FULL noPU finished.")
        with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
            sbs.write("Function FULL noPU finished. (line 684)\n")
        print()
        print()
        nopu_reco_only_creation(NEW)
        print()
        print()
        with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
            sbs.write("Function noPU RECOonly finished. (line 691)\n")
        print("Function noPU RECOonly finished.")
        FINISHED_NOPU = 1
        with open('nopu.txt','w') as nopu_made_tickets_batch_names:
            nopu_made_tickets_batch_names.write("")
print()
print()
with open("checkpoint.txt", "r+") as checkpoint_file:
    relvals_status = 0
    if not checkpoint_file.read() == "":
        #################################### noPU je nesto novo, mora da se update
        #################################### GT String nije dodat
        check_status = check_nopu_relvals_status(NEW[0][1])
        #check_status = check_nopu_relvals_status("CMSSW_12_4_6")
        print()
        print()
        print("This is check_status")
        print(check_status)
        with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
            sbs.write("This is check_status: ",check_status, " (0 - Not all the relvals are 'done', 1 - All the relvals are 'done') (line 710)\n" )
        if check_status == 1:
            gt_arr_creation(NEW)
            print()
            print()
            print("Statuses are done.")
            with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                sbs.write("Statuses are done. (line 717)\n")
            print()
            print()
            pu_reco_only_creation(PU)
            print()
            print()
            print("Function PU RECO only finished.")
            with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                sbs.write("Function PU RECO only finished. (line 725)\n")
            print()
            print()
            pu_full_creation(PU, 'HIN')
            print()
            print()
            print("Function PU HIN finished.")
            with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                sbs.write("Function PU HIN finished. (line 733)\n")
            print()
            print()
            pu_full_creation(PU, 'UPSG')
            print()
            print()
            print("Function PU UPSG finished.")
            with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                sbs.write("Function PU UPSG finished. (line 741)\n")
            print()
            print()
            pu_full_creation(PU, 'fullsim')
            print()
            print()
            print("Function PU FULLSIM finished.")
            with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
                sbs.write("Function PU FULLSIM finished. (line 749)\n")
            with open('pu.txt', 'w') as already_made_pu:
                already_made_pu.write("")
            FINISHED_PROCESS = 1       

if FINISHED_PROCESS == 1:
    with open('old.txt', 'w') as input_file:
        for rel in releases:
            input_file.write(rel[1] + '\n')           #Updating old releases for next iteration
    with open("checkpoint.txt", "w") as checkpoint_file:
        checkpoint_file.write("")
    with open('data.txt', 'w') as data_file:
        data_file.write("")
    with open("all_runs_step_by_step.txt", "a", encoding="utf-8") as sbs:
        sbs.write("____________________________________________________________________________________\n")
        sbs.write("____________________________________________________________________________________\n")
    sys.exit(5)
if FINISHED_NOPU == 1:
    with open("checkpoint.txt", "w") as checkpoint_file:
        checkpoint_file.write("The noPU tickets are made and operated")
############################# Commented out just for testing checkpoints