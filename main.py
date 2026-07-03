from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvoiceRequest(BaseModel):
    invoice_text: str

MONTHS = {
    "jan": "01", "january": "01", "feb": "02", "february": "02",
    "mar": "03", "march": "03", "apr": "04", "april": "04",
    "may": "05", "jun": "06", "june": "06", "jul": "07", "july": "07",
    "aug": "08", "august": "08", "sep": "09", "sept": "09", "september": "09",
    "oct": "10", "october": "10", "nov": "11", "november": "11",
    "dec": "12", "december": "12",
}

def parse_number(s):
    if s is None:
        return None
    s = s.replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None

def extract_invoice_no(text):
    patterns = [
        r"(?:Invoice\s*(?:No\.?\b|Number\b|#|ID\b)|Ref(?:erence)?\s*(?:No\.?)?\b|Bill\s*No\.?\b|Voucher\s*No\.?\b|Doc(?:ument)?\s*(?:No\.?|Number|ID)?\b)\s*:?\s*#?\s*([A-Za-z0-9\/\-]+)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val:
                return val
    return None

def extract_date(text):
    # Try YYYY-MM-DD directly
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # Try "15 March 2026" or "March 3, 2026"
    m = re.search(
        r"(?:Date|Issued|Dated)\s*:?\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
        text, re.IGNORECASE
    )
    if m:
        day, mon, year = m.group(1), m.group(2).lower(), m.group(3)
        if mon in MONTHS:
            return f"{year}-{MONTHS[mon]}-{day.zfill(2)}"

    m = re.search(
        r"(?:Date|Issued|Dated)\s*:?\s*([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})",
        text, re.IGNORECASE
    )
    if m:
        mon, day, year = m.group(1).lower(), m.group(2), m.group(3)
        if mon in MONTHS:
            return f"{year}-{MONTHS[mon]}-{day.zfill(2)}"

    return None

def extract_vendor(text):
    patterns = [
        r"(?:Seller|Vendor|From)\s*:?\s*(.+)",
        r"^(.+?)\s*[—\-]\s*(?:Tax\s*)?Invoice",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None

def extract_amount(text):
    patterns = [
        r"(?:Sub[\s\-]?Total|Taxable\s*(?:Value|Amount)|Net\s*Amount|Base\s*Amount|(?<!Tax\s)(?<!Total\s)(?<!Grand\s)Amount(?:\s*\(before\s*tax\))?)\s*:?\s*(?:Rs\.?|₹|INR|USD|\$|EUR|€|GBP|£)?\s*([\d,]+\.?\d*)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return parse_number(m.group(1))
    return None

def extract_tax(text):
    m = re.search(
        r"(?:IGST|GST|VAT|CGST|SGST|Tax)\s*\([\d.]+%\)\s*:?\s*(?:Rs\.?|₹|USD|\$)?\s*([\d,]+\.?\d*)",
        text, re.IGNORECASE
    )
    if m:
        return parse_number(m.group(1))
    m = re.search(r"(?:Tax|GST|VAT)\s*:?\s*(?:Rs\.?|₹|USD|\$)?\s*([\d,]+\.?\d*)", text, re.IGNORECASE)
    if m:
        return parse_number(m.group(1))
    return None

def extract_currency(text):
    if re.search(r"\bINR\b|₹|Rs\.", text):
        return "INR"
    if re.search(r"\bUSD\b|\$", text):
        return "USD"
    if re.search(r"\bEUR\b|€", text):
        return "EUR"
    if re.search(r"\bGBP\b|£", text):
        return "GBP"
    m = re.search(r"Currency\s*:?\s*([A-Z]{3})", text)
    if m:
        return m.group(1)
    return None

@app.post("/extract")
def extract(req: InvoiceRequest):
    text = req.invoice_text
    return {
        "invoice_no": extract_invoice_no(text),
        "date": extract_date(text),
        "vendor": extract_vendor(text),
        "amount": extract_amount(text),
        "tax": extract_tax(text),
        "currency": extract_currency(text),
    }

@app.get("/")
def root():
    return {"status": "ok"}
