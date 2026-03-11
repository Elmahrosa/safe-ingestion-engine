# Cost Structure

Typical infrastructure requirements include:

API server  
Worker nodes  
Redis queue  
persistent storage

Operational cost drivers:

• number of ingestion workers
• network bandwidth
• storage of sanitized content
• monitoring and logging

Scaling horizontally allows cost control by adjusting worker counts.

The architecture is designed so ingestion workers can be added or removed dynamically.
