apiVersion: apps/v1
kind: Deployment
metadata:
  name: safe-ingestion-engine
spec:
  replicas: 1
  selector:
    matchLabels:
      app: safe-ingestion-engine
  template:
    metadata:
      labels:
        app: safe-ingestion-engine
    spec:
      containers:
        - name: api
          image: your-registry/safe-ingestion-engine:latest
          ports:
            - containerPort: 8000
