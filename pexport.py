"""BNP Paribas operations importer. Creates files eaten by Skrooge."""

import pandas

import mexport


def export_operations(payees_file, bank_dump_file, mode, default_payee, unwanted_prefix):
    """Disassemble input, create and return CSV content.

    Arguments:
    files -- dictionary of constants with file names
    """

    # Difference between amount and quantity:
    # Basic currency has exchange rate 1:1, so quantity equals amount for it.
    # quantity is a value in currency specified in unit.
    # amount is a value expressed in basic currency, so it is quantity multiplied
    # by exchange rate.

    payees_dictionary = mexport.get_payees(payees_file)

    entries = []

    excel_file = pandas.read_excel(bank_dump_file)

    for record in excel_file.values:
        entry = {}

        entry['date'] = str(record[0])[0:10].replace('-', '')
        entry['mode'] = ''
        entry['payee'] = ''
        entry['comment'] = ''

        amount = float(record[2])
        entry['amount'] = str(amount)
        if amount < 0:
            entry['sign'] = '-'
        else:
            entry['sign'] = '+'

        #print(str(record[5]) + ' ' + str(record[2]))
        entry['payee'], entry['category'], \
            entry['mode'], entry['comment'] = mexport.search_payee(
                str(record[5].replace(unwanted_prefix, '')), payees_dictionary)

        if str(record[5]) == 'nan' and 'Prowizje i opłaty' in str(record[7]):
            entry['payee'] = 'Raiffeisen'
            entry['category'] = 'opłaty > raiffeisen'
            entry['mode'] = 'przelew'
            entry['comment'] = 'prowizja za wypłatę'
        if 'Odsetki' in str(record[7]):
            entry['payee'] = 'Raiffeisen'
            entry['category'] = 'opłaty > raiffeisen'
            entry['mode'] = 'przelew'
            entry['comment'] = 'odsetki'

        entry['bank'] = 'Raiffeisen'
        entry['account'] = 'Raiffeisen'
        entry['number'] = ''
        entry['unit'] = 'zł'
        entry['status'] = 'N'
        entry['tracker'] = ''
        entry['bookmarked'] = 'N'

        entries.append(entry)

    return mexport.create_csv_content(entries, mode)


if __name__ == '__main__':
    ARGUMENTS = mexport.parse_args()
    CONFIG = mexport.load_config('config.json')
    OPERATIONS_CSV = export_operations(
        ARGUMENTS['PAYEES_FILE'], ARGUMENTS['BANK_DUMP_FILE'],
        ARGUMENTS['MODE'], CONFIG['default_payee'], CONFIG['unwanted_prefix'])
    print(OPERATIONS_CSV, end='')
