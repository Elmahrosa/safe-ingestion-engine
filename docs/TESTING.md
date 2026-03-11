
# Testing

Safe Ingestion Engine includes unit tests and integration tests.

Run tests locally:

````

pytest

```

---

## Integration Tests

Integration tests validate critical ingestion safety logic.

Covered scenarios:

• policy rule enforcement  
• robots.txt blocking  
• SSRF protection  
• redirect validation

Location:

```

tests/integration/

```

---

## CI Tests

CI runs automatically on every push.

Security tools used:

• Bandit
• pip-audit
• Trivy
```

---
