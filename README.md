# AWS Document Processing Pipeline

A production-style asynchronous document processing pipeline built on AWS. Users upload files (PDF, CSV, images) via a REST API - files are stored in S3, processing jobs are queued in SQS, an EC2 worker processes them, results are saved back to S3, and an SNS notification is sent on completion. Everything runs inside a VPC with IAM role-based authentication, CloudWatch monitoring, and PostgreSQL job tracking.

---

## Architecture

```
Internet
    │
    ▼
[FastAPI on EC2 - Public Subnet]
    │                │
    │ store file      │ send job
    ▼                ▼
[S3 Raw Bucket]   [SQS Queue] ──(fail 3x)──► [Dead Letter Queue]
                      │
                      ▼
              [Worker EC2 - Private Subnet]
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
  [S3 Results]   [PostgreSQL]  [SNS Topic]
                   (RDS)           │
                                   ▼
                               [Email]

All logs ──────────────────► [CloudWatch]
```

**Key design principle:** The API never waits for processing. It accepts the file, stores it in S3, queues a job in SQS, and immediately returns `202 Accepted`. The worker processes independently and asynchronously.

---

## Tech Stack

| Category | Technology |
|----------|-----------|
| Language | Python 3.11 |
| API Framework | FastAPI + Uvicorn |
| Containerization | Docker + Docker Compose |
| File Storage | AWS S3 |
| Job Queue | AWS SQS (with Dead Letter Queue) |
| Notifications | AWS SNS |
| Compute | AWS EC2 (t2.micro) |
| Database | AWS RDS PostgreSQL |
| Authentication | AWS IAM Roles (no access keys) |
| Networking | AWS VPC (public + private subnets) |
| Monitoring | AWS CloudWatch (logs, dashboards, alarms) |
| Secrets | AWS Secrets Manager |

---

## Features

- **Asynchronous processing** - API returns `202 Accepted` immediately, never blocks
- **Automatic retry logic** - SQS retries failed jobs 3 times automatically
- **Dead Letter Queue** - failed messages preserved for inspection, never lost
- **Zero credentials on servers** - EC2 uses IAM roles, no access keys stored anywhere
- **Structured JSON logging** - every event logged as JSON, queryable in CloudWatch
- **Horizontal scaling** - run multiple worker containers against the same SQS queue
- **Network isolation** - worker and RDS in private subnet, no internet exposure
- **Encryption at rest** - S3 buckets encrypted with SSE-S3
- **Job tracking** - PostgreSQL records every job with status, timestamps, and errors
- **Fault tolerance** - `restart: always` policy auto-recovers crashed containers

---

## Project Structure

```
doc-pipeline/
├── api/                        # FastAPI application
│   ├── core/
│   │   ├── config.py           # Environment variable configuration
│   │   └── logging.py          # Structured JSON logger
│   ├── routers/
│   │   └── upload.py           # POST /api/v1/upload endpoint
│   ├── services/
│   │   ├── s3_service.py       # S3 upload logic
│   │   └── sqs_service.py      # SQS message sending
│   ├── main.py                 # FastAPI app entry point
│   ├── requirements.txt
│   └── Dockerfile
│
├── worker/                     # Background processing worker
│   ├── core/
│   │   ├── config.py           # Environment variable configuration
│   │   └── logging.py          # Structured JSON logger
│   ├── processors/
│   │   ├── pdf_processor.py    # PDF file processing logic
│   │   └── csv_processor.py    # CSV file processing logic
│   ├── services/
│   │   ├── s3_service.py       # S3 download/upload
│   │   ├── sqs_service.py      # SQS message handling
│   │   ├── sns_service.py      # SNS notification sending
│   │   ├── db_service.py       # PostgreSQL job tracking
│   │   └── secrets_service.py  # AWS Secrets Manager integration
│   ├── main.py                 # SQS polling loop
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml          # Local development setup
├── docker-compose.prod.yml     # Production EC2 setup
├── architecture.py             # Generates architecture diagram
└── README.md
```

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- Docker Desktop
- AWS CLI configured (`aws configure`)
- AWS account with S3, SQS, SNS created (see AWS Setup below)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/doc-pipeline.git
cd doc-pipeline
```

### 2. Create a `.env` file

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
AWS_REGION=us-east-1
S3_UPLOAD_BUCKET=your-raw-uploads-bucket
S3_RESULTS_BUCKET=your-results-bucket
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/doc-pipeline-queue
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:YOUR_ACCOUNT_ID:doc-pipeline-notifications
DB_HOST=
DB_NAME=pipeline_db
DB_USER=pipeline_user
DB_PASSWORD=
```

### 3. Start with Docker Compose

```bash
docker compose up --build
```

### 4. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Upload a CSV file
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@/path/to/test.csv;type=text/csv"

# Upload a PDF
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@/path/to/document.pdf;type=application/pdf"
```

### 5. View API documentation

Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser for the auto-generated Swagger UI.

---

## AWS Setup

### Required AWS Resources

Create these in order:

#### S3 Buckets
```
doc-pipeline-raw-uploads-{yourname}   ← uploaded files land here
doc-pipeline-results-{yourname}       ← processed output saved here
```
Settings: Block all public access, enable versioning on raw bucket, enable SSE-S3 encryption.

#### SQS Queues
1. Create Dead Letter Queue: `doc-pipeline-dlq` (Standard)
2. Create main queue: `doc-pipeline-queue` (Standard)
   - Visibility timeout: 60 seconds
   - Dead-letter queue: `doc-pipeline-dlq`, Max receives: 3

Add this access policy to `doc-pipeline-queue`:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "s3.amazonaws.com" },
    "Action": "SQS:SendMessage",
    "Resource": "arn:aws:sqs:REGION:ACCOUNT_ID:doc-pipeline-queue",
    "Condition": {
      "ArnLike": {
        "aws:SourceArn": "arn:aws:s3:::YOUR-RAW-BUCKET-NAME"
      }
    }
  }]
}
```

#### SNS Topic
Create topic `doc-pipeline-notifications`, add email subscription, confirm from inbox.

#### IAM Role
Create role `doc-pipeline-ec2-role` with trusted entity EC2.

Attach custom least-privilege policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": [
        "arn:aws:s3:::doc-pipeline-raw-uploads-{yourname}/*",
        "arn:aws:s3:::doc-pipeline-results-{yourname}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:SendMessage", "sqs:GetQueueAttributes"],
      "Resource": "arn:aws:sqs:us-east-1:ACCOUNT_ID:doc-pipeline-queue"
    },
    {
      "Effect": "Allow",
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:us-east-1:ACCOUNT_ID:doc-pipeline-notifications"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:ACCOUNT_ID:*"
    }
  ]
}
```

#### VPC
Create VPC `doc-pipeline-vpc` (CIDR: 10.0.0.0/16) with:
- 1 public subnet (API EC2)
- 1 private subnet (Worker EC2 + RDS)
- Internet Gateway attached

#### Security Groups
| Name | Inbound Rules |
|------|--------------|
| `doc-pipeline-api-sg` | HTTP 80, HTTPS 443, TCP 8000 from 0.0.0.0/0; SSH 22 from your IP |
| `doc-pipeline-worker-sg` | SSH 22 from your IP only |
| `doc-pipeline-rds-sg` | PostgreSQL 5432 from `doc-pipeline-worker-sg` |

#### EC2 Instances
| Instance | Subnet | Security Group | IAM Role |
|----------|--------|----------------|----------|
| `doc-pipeline-api` | Public | `doc-pipeline-api-sg` | `doc-pipeline-ec2-role` |
| `doc-pipeline-worker` | Private | `doc-pipeline-worker-sg` | `doc-pipeline-ec2-role` |

#### RDS PostgreSQL
- Instance: `doc-pipeline-db`, db.t2.micro (free tier)
- VPC: `doc-pipeline-vpc`, private subnets only
- Security Group: `doc-pipeline-rds-sg`
- Public access: No

---

## Deploying to EC2

### 1. Set permissions on your key pair
```bash
chmod 400 ~/.ssh/doc-pipeline-key.pem
```

### 2. Copy code to EC2
```bash
scp -i ~/.ssh/doc-pipeline-key.pem -r ./doc-pipeline \
  ec2-user@YOUR_EC2_PUBLIC_IP:~/doc-pipeline
```

### 3. SSH into EC2 and install Docker
```bash
ssh -i ~/.ssh/doc-pipeline-key.pem ec2-user@YOUR_EC2_PUBLIC_IP

sudo dnf install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# Install buildx and compose plugins
mkdir -p ~/.docker/cli-plugins
curl -SL https://github.com/docker/buildx/releases/download/v0.17.1/buildx-v0.17.1.linux-amd64 \
  -o ~/.docker/cli-plugins/docker-buildx
curl -SL https://github.com/docker/compose/releases/download/v2.29.1/docker-compose-linux-x86_64 \
  -o ~/.docker/cli-plugins/docker-compose
chmod +x ~/.docker/cli-plugins/docker-buildx ~/.docker/cli-plugins/docker-compose

# Log out and back in, then:
cd ~/doc-pipeline
```

### 4. Create production .env on EC2
```bash
cat > .env << 'EOF'
AWS_REGION=us-east-1
S3_UPLOAD_BUCKET=doc-pipeline-raw-uploads-yourname
S3_RESULTS_BUCKET=doc-pipeline-results-yourname
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/ACCOUNT_ID/doc-pipeline-queue
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:ACCOUNT_ID:doc-pipeline-notifications
DB_HOST=your-rds-endpoint.rds.amazonaws.com
DB_NAME=pipeline_db
DB_USER=pipeline_user
DB_PASSWORD=your-password
EOF
```

### 5. Start the pipeline
```bash
docker compose up --build -d
docker compose ps
```

### 6. Test from your local machine
```bash
curl http://YOUR_EC2_PUBLIC_IP/health
curl -X POST http://YOUR_EC2_PUBLIC_IP/api/v1/upload \
  -F "file=@/path/to/test.csv;type=text/csv"
```

---

## API Reference

### `POST /api/v1/upload`

Upload a document for async processing.

**Accepted file types:** `application/pdf`, `text/csv`, `image/png`, `image/jpeg`

**Max file size:** 10MB

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@document.pdf;type=application/pdf"
```

**Response `202 Accepted`:**
```json
{
  "status": "accepted",
  "message": "File is being processed asynchronously.",
  "s3_key": "uploads/uuid/document.pdf",
  "message_id": "sqs-message-id"
}
```

**Error responses:**
| Code | Reason |
|------|--------|
| 415 | Unsupported file type |
| 413 | File exceeds 10MB limit |
| 500 | S3 or SQS service error |

---

### `GET /health`

Health check endpoint for load balancers.

**Response `200 OK`:**
```json
{ "status": "healthy" }
```

---

## Scaling Workers

The worker scales horizontally. All worker instances pull from the same SQS queue — SQS ensures each message is processed exactly once.

```bash
# Scale to 3 workers
docker compose up -d --scale worker=3

# Check all running
docker compose ps

# Scale back down
docker compose up -d --scale worker=1
```

A CloudWatch alarm on `ApproximateNumberOfMessagesVisible > 10` signals when to scale up.

---

## Monitoring

### View live logs
```bash
# API logs
docker compose logs api --follow

# Worker logs
docker compose logs worker --follow
```

### CloudWatch
- Log group: `/doc-pipeline/api`
- Dashboard: `doc-pipeline-dashboard` (SQS queue depth, DLQ messages)
- Alarm: `doc-pipeline-dlq-not-empty` — emails on any DLQ message
- Alarm: `doc-pipeline-queue-backlog` — emails when queue depth > 10

### Query logs in CloudWatch
```
# Find all errors
{ $.level = "ERROR" }

# Find all completed jobs
{ $.action = "processing_complete" }

# Find all S3 failures
{ $.action = "s3_upload_failed" }
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_REGION` | Yes | AWS region (e.g. `us-east-1`) |
| `S3_UPLOAD_BUCKET` | Yes | S3 bucket name for raw uploads |
| `S3_RESULTS_BUCKET` | Yes | S3 bucket name for processed results |
| `SQS_QUEUE_URL` | Yes | Full SQS queue URL |
| `SNS_TOPIC_ARN` | Yes | SNS topic ARN for notifications |
| `DB_HOST` | No | RDS endpoint (leave empty to skip DB) |
| `DB_NAME` | No | PostgreSQL database name |
| `DB_USER` | No | PostgreSQL username |
| `DB_PASSWORD` | No | PostgreSQL password |
| `USE_SECRETS_MANAGER` | No | Set `true` to fetch DB creds from Secrets Manager |

---

## Security

- **IAM Roles** — EC2 instances use instance profiles. No access keys stored anywhere.
- **Least-privilege** — IAM policy scoped to specific S3 buckets, SQS queue, and SNS topic only.
- **VPC isolation** — worker and RDS in private subnet with no internet route.
- **Security Groups** — minimal inbound rules per service.
- **S3 encryption** — SSE-S3 encryption at rest on both buckets.
- **Secrets Manager** — DB credentials fetched at runtime, not stored in environment files.
- **CloudTrail** — all AWS API calls logged for audit.

---

## Database Schema

```sql
CREATE TABLE processing_jobs (
    id            SERIAL PRIMARY KEY,
    filename      VARCHAR(255) NOT NULL,
    s3_key        VARCHAR(500) NOT NULL,
    file_type     VARCHAR(50),
    status        VARCHAR(50) DEFAULT 'processing',
    result_key    VARCHAR(500),
    error_message TEXT,
    created_at    TIMESTAMP DEFAULT NOW(),
    completed_at  TIMESTAMP
);
```

---

## Cost (AWS Free Tier)

All components fit within the AWS Free Tier for development:

| Service | Free Tier Limit | Typical Usage |
|---------|----------------|---------------|
| EC2 t2.micro | 750 hrs/month | 2 instances |
| S3 | 5GB storage, 20K GET, 2K PUT | Minimal |
| SQS | 1M requests/month | Minimal |
| SNS | 1M publishes/month | Minimal |
| RDS db.t2.micro | 750 hrs/month | 1 instance |
| CloudWatch | 5GB logs/month | Minimal |

> ⚠️ Stop EC2 and RDS instances when not in use to stay within free tier limits.

---

## Phases Built

| Phase | Focus | Status |
|-------|-------|--------|
| Phase 1 | Local development, core AWS wiring (S3, SQS, SNS, Docker) | ✅ Complete |
| Phase 2 | EC2 deployment, VPC, CloudWatch, RDS | ✅ Complete |
| Phase 3 | Security hardening, scaling, IAM least-privilege, Secrets Manager | ✅ Complete |

---

## Author

**Pavan Kumar Suresh**

Built as a portfolio project demonstrating production-style AWS backend and cloud engineering skills.

- Backend: Python, FastAPI, PostgreSQL
- Cloud: AWS (EC2, S3, SQS, SNS, RDS, IAM, VPC, CloudWatch)
- DevOps: Docker, Docker Compose

---

## License

MIT
