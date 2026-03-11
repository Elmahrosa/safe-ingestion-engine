# Scaling Strategy

Safe Ingestion Engine is designed to scale progressively.

Initial deployment

SQLite storage  
single worker  
single API instance

Growth stage

PostgreSQL storage  
multiple worker processes  
dedicated Redis instance

Large-scale deployment

worker clusters  
distributed API nodes  
object storage for ingestion artifacts

Because ingestion execution is asynchronous, scaling primarily requires adding worker capacity.
