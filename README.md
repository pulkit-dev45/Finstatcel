# finstatcel

Turn PDF bank statements into clean Excel files — no manual typing, no copying stuff cell by cell.

I built this because I got tired of squinting at PDF statements from different banks, each with its own format. Instead of writing one-off scripts every time, this thing just works. Upload the PDF, pick the bank (or let it auto-detect), and you get a proper spreadsheet back.

## what it does

- parses PDF statements from major Indian banks (SBI, HDFC, ICICI, Axis, Kotak, PNB, BOB, Canara, UCO and more)
- auto-detects the bank format so you don't have to guess
- spits out a formatted Excel file with Date, Particulars, Withdrawal, Deposit, Balance columns
- keeps your data private — nothing is stored after you download

## stack

- Django 5.2
- pdfplumber for PDF parsing
- openpyxl for Excel generation
- pandas for the heavy lifting
- Three.js + GSAP on the frontend because I wanted it to look nice

## getting started

```bash
git clone https://github.com/yourusername/finstatcel.git
cd finstatcel
```

create a virtual environment and install dependencies:

```bash
python -m venv venv
venv\Scripts\activate     # windows
# or: source venv/bin/activate   # linux/mac

pip install -r requirements.txt
```

copy the environment file and tweak if needed:

```bash
copy .env.example .env     # windows
# or: cp .env.example .env  # linux/mac
```

run migrations and start the dev server:

```bash
python manage.py migrate
python manage.py runserver
```

visit `http://127.0.0.1:8000`, create an account, and you're good to go.

## env variables

| variable | what it does | default |
|---|---|---|
| `SECRET_KEY` | Django secret key | fallback dev key (change for production) |
| `DEBUG` | debug mode on/off | `False` |
| `ALLOWED_HOSTS` | comma-separated host list | `*` |

## project layout

```
finstatcel/
├── converter/              # main app — parsing, views, models
├── statementConverter/     # django project settings
├── templates/              # html templates
│   ├── converter/          # home, upload, profile pages
│   └── registration/       # login, register pages
├── static/                 # static files (empty, all inline)
├── media/                  # uploaded PDFs + generated Excel files
├── .env                    # local config (gitignored)
├── .env.example            # config template
├── .gitignore
├── manage.py
└── requirements.txt
```

## supported banks

- State Bank of India
- Axis Bank
- HDFC Bank
- ICICI Bank
- Kotak Mahindra
- Punjab National Bank
- Bank of Baroda
- Canara Bank
- UCO Bank
- works with most other Indian banks too (uses a generic fallback parser)

## want to contribute?

open an issue or send a PR. if you've got a bank statement format that doesn't work, send it over and I'll add support.
