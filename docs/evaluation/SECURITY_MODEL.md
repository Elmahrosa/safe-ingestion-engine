# Security Model

Safe Ingestion Engine is designed with multiple defensive layers.

Network Safety

SSRF protection prevents access to internal networks including:

• 127.0.0.0/8  
• 10.0.0.0/8  
• 192.168.0.0/16  
• metadata service IPs

Redirect Validation

Redirect chains are validated hop-by-hop to prevent redirect abuse.

Compliance Enforcement

robots.txt is checked before every fetch.

Domain Policy Controls

Administrators can define allow or deny rules using YAML policy files.

PII Protection

Sensitive information is scrubbed before storage:

• email
• phone
• SSN
• IPv4
• credit card numbers

Authentication

API keys are hashed before storage.

CI Security Scanning

Continuous integration includes:

Bandit  
pip-audit  
Trivy container scanning
