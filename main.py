import os
from dotenv import load_dotenv
from core.database import init_db, connect, insert_raw, log_audit
from core.pii import PIIScrubber
from collectors.scraper import SafeScraper
from core.compliance import ComplianceGuard

load_dotenv()

url = os.getenv("TARGET_URL")
allowlist = os.getenv("ALLOWLIST").split(",")

init_db()
conn = connect()

guard = ComplianceGuard(allowlist)
scraper = SafeScraper(guard, os.getenv("USER_AGENT"))
scrubber = PIIScrubber()

allowed, status, reason = guard.is_permitted(url)

if not allowed:
    log_audit(conn, url, status, reason)
    print("Blocked:", reason)
    exit()

html, ctype = scraper.fetch(url)

text, pii = scrubber.scrub(html)

insert_raw(conn, url, text, ctype, pii)
log_audit(conn, url, "SUCCESS", "Stored")

print("Stored successfully")
