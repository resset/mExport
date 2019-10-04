"""mBank operations importer. Creates files eaten by Skrooge."""

import sys
import re
import csv


def parse_args():
    """Handle command-line arguments."""

    if len(sys.argv) < 3:
        print('Usage:\n\t' + sys.argv[0] + ' payees.csv bank_dump.txt')
        exit(1)
        return None

    return {
        'PAYEES_FILE': sys.argv[1],
        'BANK_CSV_FILE': sys.argv[2]
    }


def get_payees(filename):
    """Create payees dictionary out of simple CSV file."""

    # Payees are collected this way:
    # grep -P "^[0-9]+\.[0-9]+\.[0-9]+" -A1 --color=never dump.txt \
    # | grep -P "^[^0-9\-]" --color=never
    payees = list()

    with open(filename, newline='') as csvfile:
        payee_reader = csv.reader(csvfile, delimiter=',')
        for row in payee_reader:
            payees.append(row)

    return payees


def group_lines(dump_file_content):
    """Arrange input dump file lines into groups of separate operation lines."""

    groups = []

    whites = re.compile(r'[\s]*(.*?)[\s]*\n')
    ignored_lines = ['', 'Ok?']
    date_pattern = re.compile(r'^([0-9]{2})\.([0-9]{2})\.([0-9]{4})$')

    for line in dump_file_content:
        line = whites.sub(r'\g<1>', line)

        if line in ignored_lines:
            continue
        else:
            if date_pattern.match(line):
                groups.append([])

        groups[len(groups) - 1].append(line)

    return groups


def search_payee(string, payees):
    """Searches in current operation data for known payee."""

    payee = ''
    category = ''
    mode = ''
    comment = ''
    for payee_pattern in payees:
        if payee_pattern:
            payee_regexp = re.compile('^' + payee_pattern[0] + '.*')
            if payee_regexp.match(string):
                payee = payee_pattern[1]
                if len(payee_pattern) > 2:
                    category = payee_pattern[2]
                if len(payee_pattern) > 3:
                    mode = payee_pattern[3]
                if len(payee_pattern) > 4:
                    comment = payee_pattern[4]
                # Finish search after first match
                break
    return payee, category, mode, comment


def extract_operation(group, payees):
    """Main function that creates operation record."""

    operation = {}

    # This lines ends each set of data. The list seems to be complete at least
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

    date_pattern = re.compile(r'^([0-9]{2})\.([0-9]{2})\.([0-9]{4})$')
    amount_pattern = re.compile(r'^([\-]?[ 0-9]+),([0-9]{2}) PLN$')
    whites_zahlen = re.compile(r'[\s]+')
    details_line_pattern = re.compile(r'^Szczegóły ')

    operation['lines'] = []

    operation['payee'], operation['category'], \
        operation['mode'], operation['comment'] = search_payee(
            group[1], payees)

    for line in group:
        operation['lines'].append(line)

        if date_pattern.match(line):
            # First line
            operation['date'] = date_pattern.sub(r'\3-\2-\1', line)
        elif amount_pattern.match(line):
            ones = amount_pattern.sub(r'\1', line)
            zahlen = float(whites_zahlen.sub('', ones))
            fraction = float(amount_pattern.sub(r'\2', line)) / 100.0
            if zahlen < 0:
                amount = zahlen - fraction
                operation['sign'] = '-'
            else:
                amount = zahlen + fraction
                operation['sign'] = '+'
            operation['amount'] = round(amount, 2)
        elif details_line_pattern.match(line):
            # Nothing interesting here for now
            pass
        elif line in known_modes:
            # Last line
            pass
        else:
            # Any other line
            pass
    return operation


def extract_csv_operation(csv_record, payees):
    """Main function that creates operation record from CSV data line."""

    operation = {}

    amount_pattern = re.compile(r'^([\-]?[ 0-9]+),([0-9]{2})$')
    whites_zahlen = re.compile(r'[\s]+')

    operation['lines'] = []

    if csv_record[2] == 'PRZELEW ZEWNĘTRZNY PRZYCHODZĄCY' \
        or csv_record[2] == 'PRZELEW ZEWNĘTRZNY WYCHODZĄCY':
        payee = csv_record[4]
    else:
        payee = csv_record[3]

    operation['payee'], operation['category'], \
        operation['mode'], operation['comment'] = search_payee(
            payee, payees)

    operation['date'] = csv_record[0]

    ones = amount_pattern.sub(r'\1', csv_record[6])
    zahlen = float(whites_zahlen.sub('', ones))
    fraction = float(amount_pattern.sub(r'\2', csv_record[6])) / 100.0
    if zahlen < 0:
        amount = zahlen - fraction
        operation['sign'] = '-'
    else:
        amount = zahlen + fraction
        operation['sign'] = '+'
    operation['amount'] = round(amount, 2)

    if csv_record[2] == 'WYPŁATA W BANKOMACIE':
        operation['mode'] = 'bankomat'

    if csv_record[2] == 'RĘCZNA SPŁATA KARTY KREDYT.':
        operation['payee'] = 'Mateusz'
        operation['category'] = 'transfer'
        operation['mode'] = 'przelew'

    if csv_record[2] == 'PRZELEW NA TWOJE CELE':
        operation['payee'] = 'Mateusz'
        operation['category'] = 'transfer'
        operation['mode'] = 'przelew'

    return operation


def postprocess_operations(operations):
    """Perform additional operations that will make output complete."""

    default_comment = ''
    atm_mode = 'bankomat'
    transfer_category = 'transfer'
    default_payee = ''
    default_bank = 'mBank'
    default_account = 'eKONTO'
    default_number = ''
    default_unit = 'zł'
    default_status = 'N'
    default_tracker = ''
    default_bookmarked = 'N'

    for i, operation in enumerate(operations):
        if (not 'payee' in operation or operation['payee'] == '') and len(operation['lines']) > 1:
            operations[i]['payee'] = operation['lines'][1]
        if not 'mode' in operation:
            operations[i]['mode'] = ''
        if not 'category' in operation:
            operations[i]['category'] = ''
        if not 'comment' in operation:
            operations[i]['comment'] = default_comment

        if atm_mode in operation['lines']:
            operations[i]['mode'] = atm_mode
            operations[i]['category'] = transfer_category
            operations[i]['payee'] = default_payee

        operations[i]['bank'] = default_bank
        operations[i]['account'] = default_account
        operations[i]['number'] = default_number
        operations[i]['unit'] = default_unit
        operations[i]['status'] = default_status
        operations[i]['tracker'] = default_tracker
        operations[i]['bookmarked'] = default_bookmarked

    return operations


def create_csv_content(entries):
    """Prepare CSV-formatted string with list of entries."""

    operations = ('"date";"bank";"account";"number";"mode";"payee";"comment";'
                  + '"quantity";"unit";"amount";"sign";"category";"status";'
                  + '"tracker";"bookmarked"\n')

    for entry in entries:
        operations += ('"' + str(entry['date']) + '";'
                       + '"' + str(entry['bank']) + '";'
                       + '"' + str(entry['account']) + '";'
                       + '"' + str(entry['number']) + '";'
                       + '"' + str(entry['mode']) + '";'
                       + '"' + str(entry['payee']) + '";'
                       + '"' + str(entry['comment']) + '";'
                       + '"' + str(entry['amount']) + '";'
                       + '"' + str(entry['unit']) + '";'
                       + '"' + str(entry['amount']) + '";'
                       + '"' + str(entry['sign']) + '";'
                       + '"' + str(entry['category']) + '";'
                       + '"' + str(entry['status']) + '";'
                       + '"' + str(entry['tracker']) + '";'
                       + '"' + str(entry['bookmarked']) + '";\n')

    return operations


def export_operations(files):
    """Disassemble input, create and return CSV content.

    Arguments:
    files -- dictionary of constants with file names
    """

    # Difference between amount and quantity:
    # Basic currency has exchange rate 1:1, so quantity equals amount for it.
    # quantity is a value in currency specified in unit.
    # amount is a value expressed in basic currency, so it is quantity multiplied
    # by exchange rate.

    payees_dictionary = get_payees(files['PAYEES_FILE'])

    entries = []

    with open(files['BANK_CSV_FILE'], encoding='cp1250') as bank_csv:
        csv_reader = csv.reader(bank_csv, delimiter=';')
        process_start = False
        for row in csv_reader:
            if not row:
                process_start = False

            if process_start:
                entry = extract_csv_operation(row, payees_dictionary)
                entries.append(entry)

            if row and row[0] == '#Data operacji':
                process_start = True

    entries = postprocess_operations(entries)

    return create_csv_content(entries)


if __name__ == '__main__':
    ARGUMENTS = parse_args()
    OPERATIONS_CSV = export_operations(ARGUMENTS)
    print(OPERATIONS_CSV, end='')
