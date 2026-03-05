import os
import time
from dotenv import load_dotenv
from core.database import init_db, connect, insert_raw, log_audit, log_metrics
from core.pii import PIIScrubber
from collectors.scraper import SafeScraper
from core.policy import PolicyEngine # Upgraded from ComplianceGuard

def run_ingestion(target_url):
    load_dotenv()
    
    # Initialize SaaS Engines
    init_db()
    conn = connect()
    
    # PolicyEngine handles YAML-based domain rules (SaaS Standard)
    policy_engine = PolicyEngine()
    scraper = SafeScraper(user_agent=os.getenv("USER_AGENT", "SafeSaaS/1.0"))
    scrubber = PIIScrubber()

    # 1. Policy & Compliance Check
    # This checks robots.txt, blocklists, and crawl budgets
    decision = policy_engine.evaluate(target_url)
    if not decision.allowed:
        log_audit(conn, target_url, decision.status, decision.reason)
        # Log a metric with 0 bytes to show the attempt was blocked
        log_metrics(conn, target_url, decision.status, 0, 0, "none")
        print(f"❌ Blocked: {decision.reason}")
        return

    # 2. Performance-Timed Fetch
    start_time = time.perf_counter()
    try:
        # Fetching content
        html, ctype = scraper.fetch(target_url)
        end_time = time.perf_counter()
        
        # Calculate Latency & Size (Vital for SaaS Analytics)
        elapsed_ms = int((end_time - start_time) * 1000)
        size_bytes = len(html.encode('utf-8'))
        
        # 3. Privacy Processing (PII Scrubbing)
        clean_text, pii_meta = scrubber.scrub(html)

        # 4. Storage & Audit Logging
        # insert_raw returns the row_id which can be used for Data Lineage
        row_id = insert_raw(conn, target_url, clean_text, ctype, pii_meta)
        log_audit(conn, target_url, "SUCCESS", "Stored and Scrubbed")
        
        # Log Performance Metrics for the Dashboard
        log_metrics(conn, target_url, "SUCCESS", elapsed_ms, size_bytes, ctype)
        
        print(f"✅ Success: {target_url} ({elapsed_ms}ms, {size_bytes} bytes)")

    except Exception as e:
        # Even on failure, we log the latency and the error
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        log_audit(conn, target_url, "ERROR", str(e))
        log_metrics(conn, target_url, "ERROR", elapsed_ms, 0, "unknown")
        print(f"⚠️ Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Get target from environment or CLI
    target = os.getenv("TARGET_URL")
    if target:
        run_ingestion(target)
    else:
        print("Error: No TARGET_URL found in .env")
