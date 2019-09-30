from sys import argv
import re
import csv

def parse_args():
    if len(argv) < 3:
        print('Usage:\n\t' + argv[0] + ' payees.csv bank_dump.txt')
        exit(1)
        return None

    return {
        'PAYEES_FILE': argv[1],
        'BANK_DUMP_FILE': argv[2]
    }

def export_operations(files):
    operations = ''
    default_account = 'eKONTO'
    default_number = '0'
    default_comment = ''
    default_unit = 'zł'
    atm_mode = 'bankomat'
    transfer_category = 'transfer'
    default_payee = ''

    # This lines begins each set of data. The list seems to be complete at least
    # in my case. It won't hurt to check its completeness from time to time.
    # Here is how we get it:
    # grep -P "^[0-9]+\.[0-9]+\.[0-9]+" -B1 --color=never dump.txt \
    # | grep -P "^[^0-9\-]" | sort | uniq
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

    # Payees are collected this way:
    # grep -P "^[0-9]+\.[0-9]+\.[0-9]+" -A1 --color=never dump.txt \
    # | grep -P "^[^0-9\-]" --color=never
    payees_dictionary = list()

    with open(files['PAYEES_FILE'], newline='') as csvfile:
        payee_reader = csv.reader(csvfile, delimiter=',')
        for row in payee_reader:
            payees_dictionary.append(row)

    with open(files['BANK_DUMP_FILE']) as dumpfile:

        entries = []
        current_entry = dict()
        current_entry['lines'] = list()

        whites = re.compile(r'[\s]*(.*?)[\s]*\n')
        ignored_lines = ['', 'Ok?']
        date_pattern = re.compile(r'^([0-9]{2})\.([0-9]{2})\.([0-9]{4})$')
        amount_pattern = re.compile(r'^([\-]?[ 0-9]+),([0-9]{2}) PLN$')
        whites_zahlen = re.compile(r'[\s]+')
        details_line_pattern = re.compile(r'^Szczegóły ')

        for line in dumpfile:
            line = whites.sub(r'\g<1>', line)

            if line in ignored_lines:
                continue
            else:
                # Saving whole line in case it is needed later.
                current_entry['lines'].append(line)

                if date_pattern.match(line):
                    # First line
                    current_entry['date'] = date_pattern.sub(r'\3-\2-\1', line)
                elif amount_pattern.match(line):
                    ones = amount_pattern.sub(r'\1', line)
                    zahlen = float(whites_zahlen.sub('', ones))
                    fraction = float(amount_pattern.sub(r'\2', line)) / 100.0
                    if zahlen < 0:
                        amount = zahlen - fraction
                        current_entry['sign'] = '-'
                    else:
                        amount = zahlen + fraction
                        current_entry['sign'] = '+'
                    current_entry['amount'] = round(amount, 2)
                elif details_line_pattern.match(line):
                    # Nothing interesting here
                    pass
                elif line in known_modes:
                    # Last line, current entry is done, moving to next one.
                    entries.append(current_entry)
                    current_entry = dict()
                    current_entry['lines'] = list()
                else:
                    for payee_pattern in payees_dictionary:
                        if payee_pattern:
                            payee_regexp = re.compile('^' + payee_pattern[0] + '.*')
                            if payee_regexp.match(line):
                                current_entry['payee'] = payee_pattern[1]
                                if len(payee_pattern) > 2:
                                    current_entry['category'] = payee_pattern[2]
                                if len(payee_pattern) > 3:
                                    current_entry['mode'] = payee_pattern[3]
                                if len(payee_pattern) > 4:
                                    current_entry['comment'] = payee_pattern[4]

        # Further processing
        for i, entry in enumerate(entries):
            if not 'payee' in entry or entry['payee'] == '':
                entries[i]['payee'] = entry['lines'][1]
            if not 'mode' in entry:
                entries[i]['mode'] = ''
            if not 'category' in entry:
                entries[i]['category'] = ''
            if not 'comment' in entry:
                entries[i]['comment'] = default_comment

            if atm_mode in entry['lines']:
                entries[i]['mode'] = atm_mode
                entries[i]['category'] = transfer_category
                entries[i]['payee'] = default_payee

        operations = ('"date";"account";"number";"mode";"payee";"comment";'
                      + '"quantity";"unit";"amount";"sign";"category"\n')
        for entry in entries[::-1]:
            operations += ('"' + str(entry['date']) + '";'
                           + '"' + default_account + '";'
                           + '"' + default_number + '";'
                           + '"' + str(entry['mode']) + '";'
                           + '"' + str(entry['payee']) + '";'
                           + '"' + str(entry['comment']) + '";'
                           + '"' + str(entry['amount']) + '";'
                           + '"' + default_unit + '";'
                           + '"' + str(entry['amount']) + '";'
                           + '"' + str(entry['sign']) + '";'
                           + '"' + str(entry['category']) + '";\n')
    return operations

if __name__ == '__main__':
    ARGUMENTS = parse_args()
    OPERATIONS_CSV = export_operations(ARGUMENTS)
    print(OPERATIONS_CSV, end='')
