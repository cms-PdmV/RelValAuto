"""
Program for automation of creating tickets and RelVals. The program has specified functions for
creating noPU, PU, RECO only tickets. The names of the functions are intuitive.
"""
from __future__ import print_function
import time
import xml.etree.ElementTree as ET
import os
import re
import sys
import requests
from relval import RelVal
from relmon import Relmon

# TODO: Vuk use a logger here
step_by_step = open("all_runs_step_by_step.txt", "a")


def get_releases():
    """
    This function retrieves all the CMSSW releases for each CERN OS architecture. It changes it to array of tuples
    and sorts them according to the version of the CMSSW. Every tuple is structured like:
    name of the architecture, label, type and state.
    """

    # URL to fetch XML data
    url = "https://cmssdt.cern.ch/SDT/cgi-bin/ReleasesXML?anytype=1"
    data = requests.get(url)

    with open("content.txt", "w", encoding="utf-8") as file1:
        # Write the content on a file
        file1.write(data.content.decode())

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
GT_STRING = ""
PU_TO_BE_PUSHED = []
PU = []
FULLSIM_PU = []
FULLSIM_PU_TO_BE_PUSHED = []
#NEW_TICKETS = []
FULL_PU = []
RECO_PU = []
noPU = []


def new_releases(releases):
    """
    This function checks for new releases that follow the PATTERN,
    checks the existance of old.txt file, puts new releases into
    new [] and new.txt and also updates old.txt file
    """
    global OLD
    global NEW
    # pattern = 'CMSSW(_\d{1,2}){2}_0(_pre([2-9]|(\d{2,10})))?$'
    # The regex for catching all the first releases and pres
    pattern = r'CMSSW(_\d{1,2}){2}_0(_pre([2-9]|(\d{2,10})))+$'

    # The regex for fetching all the pres
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

    with open('new.txt', 'w', encoding="utf-8") as output_file:
        for new_rel in NEW:
            output_file.write(new_rel[1] + '\n')          #Putting new releases into file

    # INFO: Vuk, what is the purpose of updating the old releases in this file?
    with open('old.txt', 'w', encoding="utf-8") as input_file:
        for rel in releases:
            input_file.write(rel[1] + '\n')           #Updating old releases for next iteration


def create_nopu_and_pu_arrays(new):
    # TODO: Vuk, instead of using global variables, return one or two array here.
    # This function will create a subset array for the noPU and PU tickets, PU means PileUp
    # We will need a relval class
    relval = RelVal()
    global noPU
    global PU
    global step_by_step

    old_tickets = relval.get('tickets', query='cmssw_release=' + OLD[-1])
    # This line gets all old tickets with specified query
    old_tickets_sort = sorted(old_tickets, key=lambda x: tuple(int(i) for i in x['_id'].split('pre')[1].split('__')[0]))

    with_noPU = ".*(noPU)+.*$"      # REGEX FOR TICKETS WITHOUT noPU (PU means PileUp)
    with_PU = ".*(PU)+.*$"          # REGEX FOR TICKETS WITH noPU

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

    # This for loop makes noPU and PU arrays
    # New tickets have the same values besides 'cmssw_release'
    # INFO: I think here, instead of writing the log by yourself, you can use the logger.
    step_by_step.write("noPU and PU arrays created\n\n") 


def creating_relvals(ticket_prepid):
    """
    This function creates release validation (RelVal) for a given ticket using its prepid
    """
    # Create an object to interact with the RelVal service
    relval = RelVal()

    # TODO: Replace with logger
    step_by_step.write("Trying to create relvals for the ticket with prepid: ")
    step_by_step.write("ticket_prepid")

    # Create the RelVal using the ticket data
    # TODO: Please save into the log the result
    response_relval = relval.create_relvals(ticket_prepid)

    # Retrieve again the RelVal using the ticket PrepId
    ticket_relvals = relval.get('relvals', query='ticket=' + ticket_prepid)

    for one_relval in ticket_relvals:
        # TODO: Use a logger
        step_by_step.write("\nPushing %s relval to next state\n" %one_relval['prepid'])
        if one_relval['status'] == 'new':
            # INFO: Vuk, the following aproves and submits the ticket, right?
            relval.next_status(one_relval['prepid'])
            step_by_step.write("Status pushed once\n")
            relval.next_status(one_relval['prepid'])
            step_by_step.write("Status pushed twice\n")
        else:
            step_by_step.write("Status is not new\n")
        # The relval status should be changed from new to submitting,
        # which is two steps ahead of new
    return ticket_relvals


def relval_status_checker(ticket_prepid):
    all_sub = 0
    while all_sub == 0:
        all_sub = 1
        step_by_step.write("Checking if all statuses are pushed properly\n")
        # TODO: I suggest you to rewrite this code section using while(True) and break statement
        # TODO: Also, why can this situation happen if your code in the forwards the status until submitted?
        # Please give more details.

        # TODO: Also, please use logger.

        # If it comes across a relval's status not pushed enough times, it pushes it again.
        # After that program's execution is postponed by 3 hours.
        ticket_relvals = relval.get('relvals', query='ticket=' + ticket_prepid)

        for rel in ticket_relvals:
            if rel['status'] != 'submitting' and rel['status'] != 'done' and rel['status'] != 'submitted':
                if rel['status'] == 'new':
                    rel.next_status(rel['prepid'])
                    rel.next_status(rel['prepid'])
                elif rel['status'] == 'approved':
                    rel.next_status(rel['prepid'])
                all_sub = 0
                step_by_step.write("Statuses are not pushed far enough.\n")
        if all_sub == 0:
            step_by_step.write("Waiting for the statuses to complete. Waiting time: 3 hours\n")
            #time.sleep(3*60*60)


def gt_string_append(ticket_relvals, ticket_batch_name):
    """
    This function appends gt string for every ticket to the gt strings array. Besides gt string,
    it also adds batch name so we can match the correct noPU tickets with correct PU tickets.
    """
    # global GT_STRING
    # global GT_STRING_ARR

    while GT_STRING == "":
        for rel in ticket_relvals:
            if rel['status'] == 'submitted' or rel['status'] == 'done':
                if rel['output_datasets'].split('/')[-1] == "GEN-SIM-RECO":
                    # INFO: This will find the last GEN-SIM-RECO ticket
                    # TODO: What happens when there are more than one ticket which fulfill the condition
                    # Both GT strings are the same?
                    GT_STRING = rel['output_datasets'].split('/')[2]
        if GT_STRING == "":
            # INFO: The pauses and retries of the script does not go here, we can retrigger it using Jenkins.
            time.sleep(3*60*60)
            # Pause it for 3 hours

    GT_STRING = GT_STRING + "_____" + ticket_batch_name.split('_')[1]
    GT_STRING_ARR.append(GT_STRING)
    GT_STRING = ""


def nopu_full_creation(new):
    """
    This function creates noPU tickets and RelVals. Argument new is array of new releases
    """
    # TODO: Please refactor to avoid using global variables
    global GT_STRING_ARR
    global PU
    global GT_STRING
    global noPU

    if len(new) == 0:       #If the new releases list is empty then there are no new releases
        print('There are no new releases')
        sys.exit(1)
    else:
        # Otherwise, we will need a relval class
        create_nopu_and_pu_arrays(new)
        if len(noPU) > 0:
            for ticket in noPU:
                # Looping through all the new tickets that need to be pushed to server
                # TODO: Please refactor using logger
                step_by_step.write("Make noPU ticket for %s\n" %(ticket['cmssw_release']))
                # INFO: Vuk, this process is just for RECO tickets?
                if not re.match('.*(RECO)+.*$', ticket['batch_name']):
                    response = relval.put('tickets', ticket)
                    inner_response = response['response']
                    ticket_prepid = inner_response['prepid']
            #Putting the ticket on the server##########################################################################
                # try:
                # #Trying to create relvals
                #     creating_relvals(ticket_prepid)
                #     step_by_step.write("Waiting for statuses to be pushed far enough. (3 hours pause)")
                #     #time.sleep(3*60*60)

                #     #Making sure all statuses are submitted or done, for the output datasets.
                #     relval_status_checker(ticket_prepid)

                #     ticket_relvals = relval.get('relvals', query='ticket=' + ticket_prepid)

                #     #We need to find gt string in the ticket and append it to the gt strings array
                #     ticket_batch_name = ticket['batch_name']
                #     gt_string_append(ticket_relvals, ticket_batch_name)
                # except KeyboardInterrupt as key_inter:
                #     step_by_step.write("The execution of the program was interrupted by keyboard interrupt: \n")
                #     step_by_step.write(key_inter)
                #     #sys.exit(2)
                # except:
                #     step_by_step.write("Can't create relvals, push the status to submitting or take GT String!\n")
        else:
            print("The noPU ticket does not exist.")


def nopu_reco_only_creation(new):
    """
    This function creates noPU tickets and RelVals. Argument new is array of new releases
    """
    # TODO: Give more details for the function comments.

    global GT_STRING_ARR
    global PU
    global GT_STRING
    global noPU

    if len(new) == 0:       #If the new releases list is empty then there are no new releases
        print('There are no new releases')
        sys.exit(1)
    else:
        #Otherwise, we will need a relval class
        # TODO: For refactor, I suggest you to use a Singleton pattern for creating this object.
        # You use it across all the script.
        relval = RelVal()
        local_gt_string = "CMSSW_12_5_0_pre3-124X_mcRun3_2022_realistic_v8-v2"
        ###############################################################################################
        
        output_datasets = []
        if len(noPU) > 0:
            for ticket in noPU:
                if re.match(".*(RECO)+.*$", ticket['batch_name']):
                    print('Make noPU RECO ticket for %s' %(ticket['cmssw_release']))
                    print("It's batch name: " + ticket['batch_name'])
                    relvals_of_ticket = relval.get('relvals', query='ticket=' + ticket['prepid'])

                    for rel in relvals_of_ticket:
                        output_datasets.append(rel['output_datasets'])

                        # TODO: For permorfance, it is not necesary to loop the whole output datasets when
                        # you get a new element. Just loop in rel[output] and then added it into the output datasets array.
                        for output in output_datasets:
                            if len(output) > 0 and output[0].split('/')[-1] == "GEN-SIM-RECO":
                                local_gt_string = output.split('/')[2]
                                break

                    # Looping through all the new tickets that need to be pushed to server
                    # Relvals have output_datasets, not tickets!
                    ticket['rewrite_gt_string'] = local_gt_string

                    response = relval.put('tickets', ticket)
                    inner_response = response['response']
                    ticket_prepid = inner_response['prepid']
                    #Putting the ticket on the server
                    # try:
                    # #Trying to create relvals
                    #     creating_relvals(ticket_prepid)
                    #     #Pause

                    #     #time.sleep(3*60*60)

                    # except KeyboardInterrupt as key_inter:
                    #     print('The execution of the program was interrupted by keyboard interrupt: ')
                    #     print(key_inter)
                    #     #sys.exit(2)
                    # except:
                    #     print("Can't create relvals, push the status to submitting or take GT String!")
                else:
                    print("This is not a proper ticket")
        else:
            print("The noPU array is empty!")


def pu_full_creation(pu, type):
    """
    The function to create PU tickets. Arguments are list of PU tickets and type. Type is a string
    which should be either 'fullsim', 'UPSG' or 'HIN'
    """
    # TODO: Refactor using Singleton
    relval = RelVal()

    if type != 'fullsim' and type != 'UPSG' and type != 'HIN':
        print('Type should be either fullsim, UPSG or HIN. Wrong type entered.')
    else:
        global NEW
        global FULL_PU
        #We want to access global variables NEW and FULL_PU
        if len(pu) > 0:
            for ticket in pu:
                # TODO: Please also use logger
                print("Ticket with the batch name:" + ticket['batch_name'] + "is being operated with")
                batch_name = ticket['batch_name'].split('_')[1]
                if batch_name == type and not ticket['batch_name'].split('_')[-2].startswith('RECO'):
                    ticket['cmssw_release'] = NEW[0][1]

                    #For now it should find just one, because we merged the similar tickets
                    #nopu_tickets = relval.get('tickets', query='cmssw_release=' + NEW[0][1] + "*")

                    #Since we need the noPU tickets before we work out PU tickets, the name is fine
                    # for nopu_ticket in nopu_tickets:
                    #     if nopu_ticket['batch_name'].split('_')[1] == type:
                    #         print("We have found the ticket with proper batch name to match with our ticket!")
                    #         i = 0
                    for gt_string in GT_STRING_ARR:
                        #print("Looking for a matching gt string with this one: " + gt_string)
                        if gt_string.split('_____')[1].startswith(type):
                            print("Matching gt string found")
                            ticket['rewrite_gt_string'] = gt_string.split('_____')[0]
                            break
                    FULL_PU.append(ticket)
                #We have created fullsim PU ticket that now can be pushed
                #time.sleep(3*60*60)
        else:
            print("The tickets of type PU do not exist.")
        if len(FULL_PU) > 0:        
            for ticket in FULL_PU:
            #Looping through all the new tickets that need to be pushed to server
                print('Make ticket for %s of the type' %(ticket['cmssw_release']))
                response = relval.put('tickets', ticket)
                inner_response = response['response']
                ticket_prepid = inner_response['prepid']
            #Putting the ticket on the server
                print("Got to the try to create relvals part")
                # try:
                #     ticket_relvals = creating_relvals(ticket_prepid)
                # except:
                #     print("Can't create relvals, push the status to submitting")
        else:
            print("Tickets of type PU FULL do not exist.")
    FULL_PU = []


def pu_reco_only_creation(pu):
    global RECO_PU
    global NEW
    if len(pu) > 0:
        for ticket in pu:
            batch_name = ticket['batch_name']
            if re.match('.*(RECO)+.*$', batch_name):
                RECO_PU.append(ticket)
        #For now it should find just one, because we merged the similar tickets
        # TODO: Refactor to use Singleton
        relval = RelVal()
    else:
        print("The tickets of type PU do not exist.")

    #We have created fullsim PU ticket that now can be pushed
    if len(RECO_PU) > 0:
        for ticket in RECO_PU:
            print('Make RECO ticket for %s' %(ticket['cmssw_release']))
        #Looping through all the new tickets that need to be pushed to server
            response = relval.put('tickets', ticket)
            inner_response = response['response']
            ticket_prepid = inner_response['prepid']
        #Putting the ticket on the server
            # try:
            #     ticket_relvals = creating_relvals(ticket_prepid)
            
            # #     time.sleep(3*60*60)
            # except KeyboardInterrupt as key_inter:
            #     print('The execution of the program was interrupted by keyboard interrupt: ')
            #     print(key_inter)
            #     sys.exit(2)
            # except:
            #     print("Can't create relvals, push the status to submitting or take GT String!")
    else:
        print("The tickets of type PU RECOonly do not exist.")


def create_relmon():
    """
    Function for creating relmon
    """
    # TODO: Refactor to use Singleton pattern
    relmon = Relmon()
    new_relmon = {}
    make_relmon = relmon.create(new_relmon)

# TODO: Refactor to use logger
step_by_step.write("The program is being executed on the date: ")
seconds = time.time()
step_by_step.write(time.ctime(seconds))
step_by_step.write("\nThese are the results:\n")

new_releases(RELEASES)
relval = RelVal()

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

step_by_step.write("\n--------------------------------------------------------------------------\n")
step_by_step.write("--------------------------------------------------------------------------\n")