import importlib
try:
    m = importlib.import_module('utils.google_sheets')
    print('Imported utils.google_sheets successfully')
    print('SHEET_NAME =', getattr(m, 'SHEET_NAME', None))
    print('SERVICE_ACCOUNT_FILE =', getattr(m, 'SERVICE_ACCOUNT_FILE', None))
    print('sheet object:', type(getattr(m, 'sheet', None)))
except Exception as e:
    print('ERROR', type(e).__name__, e)
