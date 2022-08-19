from relval import RelVal

relval = RelVal()

ticket_prepid = []

print("inside proba.py")
with open("relvals_for_pushing.txt", "r", encoding="utf-8") as file_for_relval:
    ticket_prepid = file_for_relval.readlines()

print("This is inside proba.py " + ticket_prepid[0])
ticket_relvals = relval.get('relvals', query='ticket=' + ticket_prepid[0])

print("Length of relvals array")
print(len(ticket_relvals))
print()

for rel in ticket_relvals:
    print("Prepid relvala: ", rel['prepid'])

print("Length of relvals array")
print(len(ticket_relvals))
print()

###################################################################################################################################
for rv in ticket_relvals:
    print("\nPushing %s relval to next state\n" %rv['prepid'])
    print("This is it's status: " + rv['status'])
    try:
        relval_next = RelVal()            
        relval_next.next_status(rv['prepid'])
        print("Status pushed once\n")
        relval_next.next_status(rv['prepid'])
        print("Status pushed twice\n")
    except Exception as e:
        print(e)
        print("Ovo pise kad ne moze da pushuje: ")