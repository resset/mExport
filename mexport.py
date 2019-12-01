"""mBank operations importer. Creates files eaten by Skrooge."""

import sys
import re
import csv


def parse_args():
    """Handle command-line arguments."""

    if len(sys.argv) < 3:
        print('Usage:\n\t' + sys.argv[0] + ' payees.csv bank_dump_file')
        exit(1)
        return None

    return {
        'PAYEES_FILE': sys.argv[1],
        'BANK_DUMP_FILE': sys.argv[2]
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


def extract_csv_operation(csv_record, payees):
    """Main function that creates operation record from CSV data line."""

    operation = {}

    amount_pattern = re.compile(r'^([\-]?[ 0-9]+),([0-9]{2}) PLN$')
    whites_zahlen = re.compile(r'[\s]+')

    operation['lines'] = []

    operation['date'] = csv_record[0].replace('-', '')

    ones = amount_pattern.sub(r'\1', csv_record[4])
    zahlen = float(whites_zahlen.sub('', ones))
    fraction = float(amount_pattern.sub(r'\2', csv_record[4])) / 100.0
    if zahlen < 0:
        amount = zahlen - fraction
        operation['sign'] = '-'
    else:
        amount = zahlen + fraction
        operation['sign'] = '+'
    operation['amount'] = round(amount, 2)

    operation['payee'], operation['category'], \
        operation['mode'], operation['comment'] = search_payee(
            csv_record[1], payees)

    default_payee = ''

    if 'PRZELEW ZEWNĘTRZNY' in csv_record[1]:
        operation['mode'] = 'przelew'
    elif 'PRZELEW WEWNĘTRZNY' in csv_record[1]:
        operation['payee'] = default_payee
        operation['category'] = 'transfer'
        operation['mode'] = 'przelew'
    elif 'ZAKUP PRZY UŻYCIU KARTY W KRAJU' in csv_record[1]:
        operation['mode'] = 'terminal'
    elif 'WYPŁATA GOTÓWKI W BANKOMACIE' in csv_record[1]:
        operation['payee'] = default_payee
        operation['category'] = 'transfer'
        operation['mode'] = 'bankomat'
    elif 'RĘCZNA SPŁATA KARTY KREDYT.' in csv_record[1]:
        operation['payee'] = default_payee
        operation['category'] = 'transfer'
        operation['mode'] = 'przelew'
    elif 'PRZELEW NA TWOJE CELE' in csv_record[1]:
        operation['payee'] = default_payee
        operation['category'] = 'transfer'
        operation['mode'] = 'przelew'

    if 'VISA CLASSIC CREDIT' in csv_record[2]:
        operation['account'] = 'mKarta kredytowa'
    else:
        operation['account'] = 'eKONTO'

    operation['bank'] = 'mBank'
    operation['number'] = ''
    operation['unit'] = 'zł'
    operation['status'] = 'N'
    operation['tracker'] = ''
    operation['bookmarked'] = 'N'

    return operation


def create_csv_content(entries):
    """Prepare CSV-formatted string with list of entries."""

    operations = ('"date";"bank";"account";"number";"mode";"payee";"comment";'
                  + '"quantity";"unit";"amount";"sign";"category";"status";'
                  + '"tracker";"bookmarked"\n')

    for entry in entries[::-1]:
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

    with open(files['BANK_DUMP_FILE'], encoding='cp1250') as bank_csv:
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

    return create_csv_content(entries)


if __name__ == '__main__':
    ARGUMENTS = parse_args()
    OPERATIONS_CSV = export_operations(ARGUMENTS)
    print(OPERATIONS_CSV, end='')
