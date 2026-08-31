# 🌐 NexusSwarm Enterprise Cloud Deployment Guide

This document details the production deployment architecture, continuous integration / continuous deployment (CI/CD) pipelines, and Google Cloud Platform infrastructure management for **NexusSwarm v2**.

---

## 🏛️ Production Architecture Overview

NexusSwarm runs on Google Cloud Platform using serverless container compute and managed database services:

| Component | GCP Service | Configuration Details |
| :--- | :--- | :--- |
| **API Gateway & Swarm Engine** | **Google Cloud Run** | 1 vCPU, 1GB RAM, `--no-cpu-throttling`, 300s timeout, auto-scaling (0–10 instances) |
| **Frontend Dashboard IDE** | **Google Cloud Run** | Nginx container on port 8080, 1 vCPU, 512MB RAM, 60s timeout |
| **Database & Vector Memory** | **Google Cloud SQL** | PostgreSQL 15 (`db-f1-micro` / `db-custom-2-7680`), `pgvector` enabled |
| **Artifact & Codebase Storage** | **Google Cloud Storage** | Multi-regional GCS bucket `gs://nexusswarm-outputs-${PROJECT_ID}` |
| **Secret Management** | **Google Secret Manager** | `nexusswarm-nvidia-key`, `nexusswarm-gemini-key`, `nexusswarm-db-pass` |
| **Container Registry** | **Google Artifact Registry** | Docker repository: `us-central1-docker.pkg.dev/${PROJECT_ID}/nexusswarm/` |
| **CI/CD Build Pipeline** | **Google Cloud Build** | Multi-stage Docker builds with automated secret binding |

---

## 🛠️ Step-by-Step Deployment Instructions

### Step 1: Initialize GCP Project & IAM
Set your default project and run the bootstrapping script:

```bash
gcloud config set project YOUR_PROJECT_ID
./deploy/setup.sh
```

### Step 2: Deploy Backend & Frontend Stack
Submit the Cloud Build manifest to build container images and roll out revisions:

```bash
gcloud builds submit --config=deploy/cloudbuild.yaml
```

### Step 3: Deploying Individual Updates

- **Backend / Agent Prompt changes**:
  ```bash
  gcloud builds submit --config=deploy/cloudbuild-backend.yaml
  ```

- **Frontend / React UI changes**:
  ```bash
  gcloud builds submit --config=deploy/cloudbuild-frontend.yaml
  ```

---

## 🛡️ Critical Cloud Run Performance & Reliability Rules

1. **Continuous CPU Allocation (`--no-cpu-throttling`)**:
   NexusSwarm schedules multi-pipeline agent swarms as background `asyncio` tasks after returning HTTP 200 on task submission. Without `--no-cpu-throttling`, Cloud Run pauses container execution outside active HTTP requests, causing external API socket read timeouts.

2. **Long Timeout Budgets (`--timeout=300`)**:
   Agentic task decomposition and code generation across 20+ specialized agents requires adequate execution buffers.

3. **Dual-Provider Resilience (NVIDIA NIM + Gemini)**:
   The backend routes to NVIDIA NIM for primary reasoning and automatically fails over to Google Gemini (`gemini-2.0-flash`) if NIM experiences rate-limiting or latency.

---

## 📊 Monitoring & Health Checks

Monitor system telemetry and logs:

```bash
# Stream backend logs
gcloud beta run services logs tail nexusswarm-backend --region=us-central1

# Query live service health
curl -s https://nexusswarm-backend-669943047856.us-central1.run.app/health | jq .
```
