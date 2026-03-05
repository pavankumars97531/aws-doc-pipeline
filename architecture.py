from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2
from diagrams.aws.storage import S3
from diagrams.aws.integration import SQS, SNS
from diagrams.aws.management import Cloudwatch
from diagrams.aws.database import RDS
from diagrams.aws.network import VPC, InternetGateway
from diagrams.aws.security import IAM
from diagrams.onprem.client import User
from diagrams.onprem.container import Docker

with Diagram(
    "AWS Document Processing Pipeline",
    filename="architecture",
    show=False,
    direction="LR"
):
    user = User("Client")

    with Cluster("AWS VPC"):
        igw = InternetGateway("Internet Gateway")

        with Cluster("Public Subnet"):
            api = EC2("API EC2\n(FastAPI)")
            api_docker = Docker("Docker\nContainer")

        with Cluster("Private Subnet"):
            worker = EC2("Worker EC2")
            worker_docker = Docker("Docker\nContainer")
            db = RDS("PostgreSQL\nRDS")

        with Cluster("AWS Managed Services"):
            raw_bucket = S3("S3 Raw\nUploads")
            results_bucket = S3("S3 Results")
            queue = SQS("SQS Queue")
            dlq = SQS("Dead Letter\nQueue")
            topic = SNS("SNS Topic")
            logs = Cloudwatch("CloudWatch\nLogs")
            iam = IAM("IAM Role")

    user >> igw >> api
    api >> raw_bucket
    api >> queue
    queue >> Edge(label="retry x3") >> dlq
    queue >> worker
    worker >> results_bucket
    worker >> topic
    worker >> db
    api >> logs
    worker >> logs
    iam >> Edge(style="dashed") >> api
    iam >> Edge(style="dashed") >> worker