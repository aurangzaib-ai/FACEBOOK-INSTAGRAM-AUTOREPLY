import os
# ensure env var isn't used for this test
os.environ.pop('GOOGLE_SHEET_NAME', None)
from utils.google_sheets import get_sheet
try:
    s = get_sheet()
    print('Opened sheet using core.config:', type(s))
except Exception as e:
    print('ERROR', type(e).__name__, e)
