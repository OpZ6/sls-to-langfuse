SLS to Langfuse Real-time Sync Service
<p align="left"> <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"> <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11"> <img src="https://img.shields.io/badge/阿里云-SLS-FF6A00?style=for-the-badge&logo=alibabacloud&logoColor=white" alt="Alibaba Cloud SLS"> <img src="https://img.shields.io/badge/Langfuse-Integration-5A34D2?style=for-the-badge" alt="Langfuse"> </p>
A high-performance, real-time data synchronization service that automatically parses AI gateway access logs from Alibaba Cloud SLS and sends them to Langfuse for AI application observability and analysis.

🎯 Core Features
✅ Real-time Consumption: Achieves millisecond-level log synchronization based on Alibaba Cloud SLS Consumer Groups.
✅ Intelligent Parsing: Automatically identifies and parses conversational data from AI gateway logs.
✅ Reliable Transmission: Ensures no data loss with a built-in retry mechanism and dead-letter queue.
✅ Performance Optimized: Handles high concurrency with support for parallel consumption across multiple shards.
✅ Monitoring Friendly: Provides detailed logging and processing statistics for easy observation.
✅ Environment Adaptive: Supports different configurations for development and production environments.
⚠️ Important Prerequisites
Before you begin, please ensure your environment meets the following requirements. Failure to meet these conditions is the most common cause of deployment issues.

1. AI Gateway Configuration
Your AI Gateway must be configured to output access logs to Alibaba Cloud SLS. The log format is critical for the service to function correctly.

Enable Tracing: The gateway's tracing or logging feature must be active.
JSON Log Format: Logs must be in JSON format and contain a specific ai_log field, which itself is a JSON string.
Required Fields: The log entry must include the following key fields:
json
{
      "trace_id": "unique-trace-id-for-the-request",
      "question": "The user's input/prompt",
      "answer": "The AI's response",
      "ai_log": "{\"model_name\":\"qwen-vl\", \"usage\":{\"total_tokens\": 120}}",
      "response_code": 200,
      "duration": 540
    }
2. Infrastructure Requirements
Alibaba Cloud SLS: An active SLS project and Logstore are required.
Langfuse Instance: A running and accessible Langfuse service (self-hosted or cloud).
Docker Environment: Docker 20.10+ installed on your server.
Network Connectivity: The server/container must have network access to both the Alibaba Cloud SLS endpoint and your Langfuse host.
🚀 Quick Start & Deployment
Follow these steps to get the service running.

1. Clone the Repository
bash
git clone https://github.com/your-username/sls-to-langfuse.git
cd sls-to-langfuse
2. Configure Environment Variables
The service is configured entirely through environment variables. Create a .env file from the example.

bash
cp .env.example .env
Now, edit the .env file with your specific credentials and endpoints.

bash
# .env

# ======== Alibaba Cloud SLS Configuration ========
ALIYUN_ENDPOINT=cn-shanghai.log.aliyuncs.com  # Adjust to your SLS region
ALIYUN_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID       # Your Alibaba Cloud Access Key
ALIYUN_ACCESS_KEY_SECRET=YOUR_ACCESS_SECRET   # Your Alibaba Cloud Access Secret
ALIYUN_PROJECT_NAME=your-sls-project-name     # Your SLS Project
ALIYUN_LOGSTORE_NAME=your-logstore-name       # Your SLS Logstore
ALIYUN_CONSUMER_GROUP_NAME=langfuse-consumer-prod-v1 # A custom name for the consumer group (see notes below)

# ======== Langfuse Configuration ========
LANGFUSE_HOST=https://your-langfuse-instance.com # Your Langfuse host URL
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxxxxxx # Your Langfuse public key
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxxxxxx # Your Langfuse secret key
LANGFUSE_SDK_TIMEOUT=30                      # SDK timeout in seconds (optional)

# ======== Application & Logging Configuration ========
TZ=Asia/Shanghai          # Set container timezone (e.g., Asia/Shanghai)
LOG_FORMAT=json           # Log format: 'human' for development, 'json' for production
3. Deploy with the Script
The provided deploy.sh script automates the entire process of pulling the latest code, rebuilding the Docker image, and restarting the container.

bash
# Make the script executable
chmod +x deploy.sh

# Run the deployment
./deploy.sh
4. Verify the Service
Check the container's status and logs to ensure it's running correctly.

bash
# Check if the container is running
docker ps | grep sls_processor_instance

# View real-time logs
docker logs -f sls_processor_instance
If everything is configured correctly, you should see logs indicating that the service has started and is attempting to pull data from your SLS shards.

🐳 Docker Image & Customization
Image Source
Note To improve build speeds for users in mainland China, the Dockerfile uses a Python base image from a Huawei Cloud mirror.

dockerfile
> FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/python:3.11-slim
>
If you are outside of China or prefer using the official Docker Hub source, please modify the Dockerfile to:

dockerfile
> FROM python:3.11-slim
>
Similarly, Python dependencies are installed using a Tsinghua pip mirror. This can be removed in the RUN command inside the Dockerfile if not needed.

Custom Builds
If you make changes to the source code, you can build and push your own image:

bash
# Build a custom image
docker build -t your-registry/sls-to-langfuse:latest .

# Push to a private registry
docker push your-registry/sls-to-langfuse:latest
⚙️ Detailed Configuration
Environment Variables
Variable	Required	Default Value	Description
ALIYUN_ENDPOINT	✅	—	Alibaba Cloud SLS endpoint for your region.
ALIYUN_ACCESS_KEY_ID	✅	—	Your Alibaba Cloud Access Key ID.
ALIYUN_ACCESS_KEY_SECRET	✅	—	Your Alibaba Cloud Access Key Secret.
ALIYUN_PROJECT_NAME	✅	—	The name of your SLS Project.
ALIYUN_LOGSTORE_NAME	✅	—	The name of your SLS Logstore where gateway logs are stored.
ALIYUN_CONSUMER_GROUP_NAME	✅	—	Crucial: A unique name for the consumer group. See the note below.
LANGFUSE_HOST	✅	—	The full URL of your Langfuse instance.
LANGFUSE_PUBLIC_KEY	✅	—	The public key from your Langfuse project.
LANGFUSE_SECRET_KEY	✅	—	The secret key from your Langfuse project.
LANGFUSE_SDK_TIMEOUT	❌	30	Timeout in seconds for requests made to the Langfuse API.
TZ	❌	UTC	Timezone for the container to ensure logs have correct timestamps.
LOG_FORMAT	❌	human	human for readable logs (dev), json for structured logs (prod).
⚠️ A Note on ALIYUN_CONSUMER_GROUP_NAME This name determines where the service starts reading logs.

Using the same name allows the service to pick up where it left off.
Changing the name will cause the service to start consuming all logs from the very beginning, which can lead to massive data duplication in Langfuse.
It is recommended to use different names for different environments (e.g., langfuse-consumer-dev, langfuse-consumer-prod).

🔍 Monitoring & Troubleshooting
Common Problems
Container Fails to Start:

Check the .env file: Ensure all required variables are set and there are no syntax errors.
Check permissions: Ensure the user running the Docker command has permissions to access the Docker daemon.
No Logs Being Consumed:

Check IAM Permissions: The Alibaba Cloud Access Key needs permissions for SLS, including:
log:GetConsumerGroupCheckPoint
log:UpdateConsumerGroup
log:ConsumerGroupUpdateCheckPoint
log:ListConsumerGroup
log:PullLogs
Check Network Connectivity: From within the container, try to ping the SLS endpoint.
bash
docker exec -it sls_processor_instance ping cn-shanghai.log.aliyuncs.com
Langfuse Connection Failed:
Check Host and Keys: Double-check that LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, and LANGFUSE_SECRET_KEY are correct.
Test Health Endpoint: Use curl to see if the Langfuse instance is reachable from the server.
bash
curl -X GET "https://your-langfuse-instance.com/api/public/health"
Duplicate Data in Langfuse:
This is almost always caused by changing the ALIYUN_CONSUMER_GROUP_NAME or manually deleting a consumer group in the SLS console, which resets the consumption checkpoint. Always use a consistent name.
Useful Commands
bash
# View service status
docker ps | grep sls_processor

# Gracefully restart the service with the latest code
./deploy.sh

# View the last 100 lines of logs and follow in real-time
docker logs --tail 100 -f sls_processor_instance

# Enter the container for debugging
docker exec -it sls_processor_instance /bin/bash

# Stop and remove the service container
docker stop sls_processor_instance && docker rm sls_processor_instance
