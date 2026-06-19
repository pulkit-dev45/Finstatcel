import re
import logging
import pdfplumber
import pandas as pd

logger = logging.getLogger(__name__)

DATE_AT_START = re.compile(
    r'^(?:\d{1,3}\s+)?(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}|\d{1,2}[./-][A-Za-z]{3,9}[./-]\d{2,4})\s+(.*)',
    re.IGNORECASE
)

HEADER_LINE_KEYWORDS = [
    'statement', 'account', 'branch', 'ifsc', 'micr', 'customer',
    'address', 'period', 'page', 'summary', 'opening', 'closing',
    'statement of account', 'generated on', 'printed on', 'statement for',
    'ref no', 'mobile no', 'email', 'a/c type', 'a/c no',
    'legend', 'system generated', 'never share your',
    'www.', 'dial your bank',
]

BANK_HEADERS = {
    'sbi': {
        'date': ['date', 'txn date', 'transaction date', 'value date'],
        'particulars': ['particulars', 'narration', 'description', 'transaction details', 'remarks'],
        'withdrawal': ['debit', 'dr', 'withdrawal', 'withdrawn'],
        'deposit': ['credit', 'cr', 'deposit', 'deposited'],
        'balance': ['balance', 'closing balance'],
    },
    'axis': {
        'date': ['date', 'txn date', 'transaction date', 'value date', 'posting date'],
        'particulars': ['particulars', 'narration', 'description', 'transaction details', 'remarks'],
        'withdrawal': ['debit', 'withdrawal', 'withdrawn'],
        'deposit': ['credit', 'deposit', 'deposited'],
        'balance': ['balance', 'closing balance', 'available balance'],
        'amount': ['amount'],
        'drcr': ['debit/credit', 'dr/cr', 'drcr'],
    },
    'icici': {
        'date': ['date', 'txn date', 'transaction date', 'value date'],
        'particulars': ['particulars', 'narration', 'description', 'transaction details',
                        'remarks', 'chq/ref no', 'chq no', 'cheque no', 'ref no'],
        'withdrawal': ['withdrawal', 'withdrawn', 'debit', 'dr'],
        'deposit': ['deposit', 'deposited', 'credit', 'cr'],
        'balance': ['balance', 'closing balance'],
    },
    'hdfc': {
        'date': ['date', 'txn date', 'transaction date', 'value date', 'posting date'],
        'particulars': ['particulars', 'narration', 'description', 'transaction details',
                        'remarks', 'chq no', 'cheque no', 'cheque number'],
        'withdrawal': ['debit', 'dr', 'withdrawal', 'withdrawn', 'debit amount'],
        'deposit': ['credit', 'cr', 'deposit', 'deposited', 'credit amount'],
        'balance': ['balance', 'closing balance'],
    },
    'kotak': {
        'date': ['date', 'txn date', 'transaction date', 'value date'],
        'particulars': ['particulars', 'narration', 'description', 'transaction details',
                        'remarks', 'chq no', 'cheque no'],
        'withdrawal': ['withdrawal', 'withdrawn', 'debit', 'dr'],
        'deposit': ['deposit', 'deposited', 'credit', 'cr'],
        'balance': ['balance', 'closing balance'],
    },
    'pnb': {
        'date': ['date', 'txn date', 'transaction date', 'value date'],
        'particulars': ['particulars', 'narration', 'description', 'transaction details', 'remarks'],
        'withdrawal': ['debit', 'dr', 'withdrawal', 'withdrawn'],
        'deposit': ['credit', 'cr', 'deposit', 'deposited'],
        'balance': ['balance', 'closing balance'],
    },
    'bob': {
        'date': ['date', 'txn date', 'transaction date', 'value date', 'posting date'],
        'particulars': ['particulars', 'narration', 'description', 'transaction details',
                        'remarks', 'chq no', 'ref no'],
        'withdrawal': ['withdrawal', 'withdrawn', 'debit', 'dr', 'debit amount'],
        'deposit': ['deposit', 'deposited', 'credit', 'cr', 'credit amount'],
        'balance': ['balance', 'closing balance', 'available balance'],
    },
    'canara': {
        'date': ['date', 'txn date', 'transaction date', 'value date'],
        'particulars': ['particulars', 'narration', 'description', 'transaction details', 'remarks'],
        'withdrawal': ['debit', 'dr', 'withdrawal', 'withdrawn'],
        'deposit': ['credit', 'cr', 'deposit', 'deposited'],
        'balance': ['balance', 'closing balance'],
    },
    'federal': {
        'date': ['date', 'txn date', 'transaction date', 'value date'],
        'particulars': ['particulars', 'narration', 'description', 'transaction details',
                        'remarks', 'chq/ref no', 'ref no'],
        'withdrawal': ['debit', 'dr', 'withdrawal', 'withdrawn'],
        'deposit': ['credit', 'cr', 'deposit', 'deposited'],
        'balance': ['balance', 'closing balance'],
    },
    'indusind': {
        'date': ['date', 'txn date', 'transaction date', 'value date', 'posting date'],
        'particulars': ['particulars', 'narration', 'description', 'transaction details',
                        'remarks', 'chq no', 'ref no'],
        'withdrawal': ['debit', 'dr', 'withdrawal', 'withdrawn', 'debit amount'],
        'deposit': ['credit', 'cr', 'deposit', 'deposited', 'credit amount'],
        'balance': ['balance', 'closing balance', 'available balance'],
    },
}
DEFAULT_HEADERS = {
    'date': ['date', 'txn date', 'transaction date', 'value date', 'posting date', 'value dt'],
    'particulars': ['particulars', 'narration', 'description', 'transaction details',
                    'transaction', 'remarks', 'details'],
    'withdrawal': ['withdrawal', 'withdrawn', 'debit', 'dr', 'debit amount'],
    'deposit': ['deposit', 'deposited', 'credit', 'cr', 'deposit amount', 'credit amount'],
    'balance': ['balance', 'closing balance', 'available balance', 'running balance'],
    'amount': ['amount'],
}

# Banks whose PDFs are known to NOT have extractable tables → skip table phase
TEXT_ONLY_BANKS = {'uco'}


def _get_headers(bank):
    if bank in BANK_HEADERS:
        return BANK_HEADERS[bank]
    return DEFAULT_HEADERS


def _is_header(text):
    low = text.strip().lower()
    if not low or len(low) <= 2:
        return True
    if any(k in low for k in HEADER_LINE_KEYWORDS):
        return True
    return False


def _parse_num(text):
    try:
        cleaned = re.sub(r'[^\d.,]', '', text)
        cleaned = cleaned.replace(',', '')
        if not cleaned or cleaned == '.':
            return None
        return float(cleaned)
    except ValueError:
        return None


def _clean_text(text):
    return re.sub(r'\s+', ' ', text.strip())


# ── TABLE EXTRACTION ─────────────────────────────────────────────────

def _map_headers(row, bank):
    col_map = _get_headers(bank)
    mapping = {}
    for i, cell in enumerate(row):
        nh = re.sub(r'\s+', ' ', str(cell or '').strip().lower())
        for key, kws in col_map.items():
            if any(k in nh for k in kws):
                if key not in mapping:
                    mapping[key] = i
                break
    return mapping


def _find_header_row(table, bank):
    for row_idx, row in enumerate(table):
        mapping = _map_headers([str(c or '') for c in row], bank)
        if 'date' in mapping and 'balance' in mapping:
            return row_idx, mapping
    return None, None


def try_table(pdf_path, bank):
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if len(table) < 2:
                    continue
                header_row_idx, mapping = _find_header_row(table, bank)
                if mapping is None:
                    continue
                wi = mapping.get('withdrawal', -1)
                depi = mapping.get('deposit', -1)
                ami = mapping.get('amount', -1)
                has_w = wi >= 0
                has_d = depi >= 0
                combined_drcr = ami >= 0 and (wi == depi or has_w != has_d)

                rows = []
                for row in table[header_row_idx + 1:]:
                    try:
                        di = mapping['date']
                        d = str(row[di]).strip() if di < len(row) else ''
                        pi = mapping.get('particulars', -1)
                        p = str(row[pi]).strip() if 0 <= pi < len(row) else ''
                        bi = mapping['balance']
                        b = str(row[bi]).strip() if bi < len(row) else ''
                    except (IndexError, KeyError):
                        continue
                    d = re.sub(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}).*', r'\1', d)
                    if not re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', d):
                        continue
                    p = p.replace('\n', ', ').replace('\r', ', ')
                    p = re.sub(r'\s+', ' ', p).strip()
                    if combined_drcr:
                        raw_amt = str(row[ami]).strip() if ami < len(row) else ''
                        raw_flag = str(row[wi]).strip().lower() if wi < len(row) else ''
                        av = _parse_num(raw_amt) or 0
                        wv = av if raw_flag in ('dr', 'd') else 0
                        dv = av if raw_flag in ('cr', 'c') else 0
                    else:
                        w = str(row[wi]).strip() if 0 <= wi < len(row) else ''
                        dep = str(row[depi]).strip() if 0 <= depi < len(row) else ''
                        wv = _parse_num(w) or 0
                        dv = _parse_num(dep) or 0
                    bv = _parse_num(b) or 0
                    if bv == 0 and wv == 0 and dv == 0:
                        continue
                    rows.append({'Date': d, 'Particulars': p,
                                 'Withdrawn amount': wv, 'Deposit amount': dv, 'Balance': bv})
                if len(rows) >= 3:
                    return rows
    return None


# ── TEXT EXTRACTION ───────────────────────────────────────────────────

def _get_numbers(text):
    text = re.sub(r'\d{8,}', ' ', text)
    text = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', ' ', text)
    text = re.sub(r'\b\d{1,2}[/-][A-Za-z]{3,9}[/-]\d{2,4}\b', ' ', text)
    text = re.sub(r'\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}\b', ' ', text)
    text = re.sub(r'\b\d{1,2}:\d{2}(:\d{2})?\b', ' ', text)
    combined = re.finditer(r'[\d,]+\.\d+|(?<!\d)\d{1,7}(?!\d)', text)
    raw_nums = []
    for m in combined:
        raw = m.group()
        if '.' in raw and len(raw.split('.')) > 2:
            continue
        v = _parse_num(raw)
        if v is not None and 0 < v < 99999999:
            raw_nums.append((v, '.' in raw, m.start()))
    if not raw_nums:
        return []
    dec_count = sum(1 for _, has_dot, _ in raw_nums if has_dot)
    if dec_count >= 2:
        nums = [v for v, has_dot, _ in raw_nums if has_dot]
    else:
        nums = [v for v, _, _ in raw_nums]
    return nums


SKIP_LINES = {
    'credit trxn', 'debit trxn', 'fund transfer', 'idirect trxn', 'nach trxn',
}


def try_text(pdf_path):
    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                lines.extend(t.split('\n'))

    transactions = []
    prev_bal = None
    drcr_flag = None

    for line in lines:
        raw = line.strip()
        if not raw or _is_header(raw):
            continue

        low = raw.lower()
        if low in SKIP_LINES:
            if 'credit' in low and 'trxn' in low:
                drcr_flag = 'credit'
            elif 'debit' in low and 'trxn' in low:
                drcr_flag = 'debit'
            continue

        m = DATE_AT_START.match(raw)
        if not m:
            if transactions:
                transactions[-1]['parts'].append(raw)
            continue

        date = m.group(1)
        rest = m.group(2)
        nums = _get_numbers(rest)

        if len(nums) < 2:
            if transactions:
                transactions[-1]['parts'].append(raw)
            continue

        balance = nums[-1]
        amounts = nums[:-1]

        transactions.append({
            'date': date,
            'parts': [],
            'balance': balance,
            'amounts': amounts,
            'prev_bal': prev_bal,
            'drcr': drcr_flag,
        })
        prev_bal = balance
        drcr_flag = None

        parts_text = rest
        parts_text = re.sub(r'[\d,]+(?:\.\d+)?', ' ', parts_text)
        parts_text = re.sub(r'\s+', ' ', parts_text).strip()
        if parts_text:
            transactions[-1]['parts'].append(parts_text)

    return transactions


def _resolve_amounts(transactions):
    rows = []
    for txn in transactions:
        amounts = txn['amounts']
        balance = txn['balance']
        prev_bal = txn['prev_bal']
        drcr = txn.get('drcr')
        w = 0.0
        d = 0.0

        if drcr == 'credit':
            if amounts:
                d = amounts[0] if len(amounts) == 1 else amounts[1]
        elif drcr == 'debit':
            if amounts:
                w = amounts[0] if len(amounts) == 1 else amounts[1]
        elif len(amounts) == 1:
            amt = amounts[0]
            if prev_bal is not None:
                diff = balance - prev_bal
                if abs(diff - amt) < 0.01:
                    d = amt
                elif abs(diff + amt) < 0.01:
                    w = amt
                elif abs(prev_bal + amt - balance) < 0.01:
                    d = amt
                elif abs(prev_bal - amt - balance) < 0.01:
                    w = amt
                elif diff > 0.01:
                    d = diff
                elif diff < -0.01:
                    w = -diff
                else:
                    w = amt
            else:
                w = amt
                d = 0.0
        elif len(amounts) >= 2:
            w, d = amounts[0], amounts[1]
            if w > 0 and d > 0 and prev_bal is not None:
                if abs(prev_bal + d - balance) < abs(prev_bal - w - balance):
                    w = 0.0
                else:
                    d = 0.0
            if w > 0 and d > 0:
                diff = balance - prev_bal if prev_bal is not None else 0
                if diff > 0.01:
                    w = 0.0
                    d = diff
                elif diff < -0.01:
                    d = 0.0
                    w = -diff
        else:
            continue

        parts = ' '.join(txn['parts'])
        parts = _clean_text(parts)
        if not parts:
            parts = 'Transaction'

        rows.append({
            'Date': txn['date'],
            'Particulars': parts,
            'Withdrawn amount': w,
            'Deposit amount': d,
            'Balance': balance,
        })

    return rows


# ── MAIN ENTRY POINT ──────────────────────────────────────────────────

def parse_statement_pdf(pdf_path, bank='auto'):
    table_rows = None
    if bank not in TEXT_ONLY_BANKS:
        table_rows = try_table(pdf_path, bank)
    if table_rows:
        logger.info(f"Table extraction ({bank}): {len(table_rows)} rows")
        return _make_df(table_rows)

    logger.info(f"No table found for '{bank}', trying text extraction")
    transactions = try_text(pdf_path)
    if transactions:
        rows = _resolve_amounts(transactions)
        if rows:
            logger.info(f"Text extraction ({bank}): {len(rows)} rows")
            return _make_df(rows)

    logger.warning(f"No transaction data found ({bank})")
    return pd.DataFrame(columns=['Date', 'Particulars', 'Withdrawn amount', 'Deposit amount', 'Balance'])


def _make_df(rows):
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    if 'Date' in df.columns:
        df['Date'] = df['Date'].str.replace('.', '/', regex=False)
    df = df.drop_duplicates(subset=['Date', 'Balance'])
    df = df.reset_index(drop=True)
    return df
