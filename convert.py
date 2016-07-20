import re
import csv
#TODO: if not needed, delete it
import pprint

BANK_DUMP_FILE = 'dump.txt'
PAYEES_FILE = 'payees.csv'

default_account = 'eKONTO'
default_number = '0'
default_comment = ''
default_unit = 'zł'

# This lines end sets of data. The list should be updated. Here is how we get it:
# cat dump.txt | grep -P "^[0-9]+\.[0-9]+\.[0-9]+" -B1 --color=never | grep -P "^[^0-9\-]" | sort | uniq
known_modes = [
    'Inna operacja',
    'Nierozliczone',
    'Operacja gotówkowa',
    'Przelew',
    'Płatność kartą'
    ]

# Difference between amount and quantity:
# Basic currency has exchange rate 1:1, so quantity equals amount for it.
# quantity is a value in currency specified in unit.
# amount is a value expressed in basic currency, so it is quantity multiplied
# by exchange rate.

payees_dictionary = list()

with open(PAYEES_FILE, newline='') as csvfile:
    payee_reader = csv.reader(csvfile, delimiter=',')
    for row in payee_reader:
        payees_dictionary.append(row)

with open(BANK_DUMP_FILE) as f:

    entries = []
    current_entry = dict()
    current_entry['lines'] = list()

    for line in f:
        whites_bgn = re.compile('^[\s]+')
        line = whites_bgn.sub('', line)
        whites_end = re.compile('[\s]+$')
        line = whites_end.sub('', line)

        #TODO: fix this regex and delete two previous ones
        #whites = re.compile('^[\s]*(.*?)[\s]*$')
        #line = whites.sub('\0', line)

        if '' == line:
            continue
        else:
            # Saving whole line in case it is needed later.
            current_entry['lines'].append(line)

            date_pattern = re.compile('^([0-9]{2})\.([0-9]{2})\.([0-9]{4})$')
            amount_pattern = re.compile('^([\-]?[ 0-9]+),([0-9]{2}) PLN$')
            if date_pattern.match(line):
                current_entry['date'] = date_pattern.sub(r'\3-\2-\1', line)
            elif amount_pattern.match(line):
                ones = amount_pattern.sub(r'\1', line)
                whites = re.compile('[\s]+')
                zahlen = float(whites.sub('', ones))
                fraction = float(amount_pattern.sub(r'\2', line)) / 100.0
                if 0 > zahlen:
                    sum = zahlen - fraction
                    current_entry['sign'] = '-'
                else:
                    sum = zahlen + fraction
                    current_entry['sign'] = '+'
                current_entry['amount'] = sum
            elif line in known_modes:
                # Current entry is done, moving to next one.
                entries.append(current_entry)
                current_entry = dict()
                current_entry['lines'] = list()
            else:
                for payee_pattern in payees_dictionary:
                    if 0 < len(payee_pattern):
                        payee_regexp = re.compile('^' + payee_pattern[0] + '.*')
                        if payee_regexp.match(line):
                            current_entry['payee'] = payee_pattern[1]
                            if 2 < len(payee_pattern):
                                current_entry['category'] = payee_pattern[2]
                            if 3 < len(payee_pattern):
                                current_entry['mode'] = payee_pattern[3]
                            if 4 < len(payee_pattern):
                                current_entry['comment'] = payee_pattern[4]

    # Further processing
    for i, entry in enumerate(entries):
        if not 'payee' in entry:
            entries[i]['payee'] = ''
        if not 'category' in entry:
            entries[i]['category'] = ''
        if not 'comment' in entry:
            entries[i]['comment'] = default_comment

        if 'Wypłata gotówki' in entry['lines']:
            entries[i]['mode'] = 'bankomat'

    print('"date";"account";"number";"mode";"payee";"comment";"quantity";"unit";"amount";"sign";"category"')
    for entry in entries:
        print(  '"' + str(entry['date']) + '";'
              + '"' + default_account + '";'
              + '"' + default_number + '";'
              + '"' + str(entry['mode']) + '";'
              + '"' + str(entry['payee']) + '";'
              + '"' + str(entry['comment']) + '";'
              + '"' + str(entry['amount']) + '";'
              + '"' + default_unit + '";'
              + '"' + str(entry['amount']) + '";'
              + '"' + str(entry['sign']) + '";'
              + '"' + str(entry['category']) + '";')
