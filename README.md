📊 SLS to Langfuse Real-time Sync Service





🚀 一个高性能的实时数据同步服务，将阿里云SLS中的AI网关访问日志自动解析并发送到Langfuse，用于AI应用的观测和分析。

🎯 功能特性

✅ 实时消费：基于阿里云SLS Consumer Group，实现毫秒级日志同步
✅ 智能解析：自动识别和解析AI网关日志中的对话数据
✅ 可靠传输：内置重试机制和死信队列，确保数据不丢失
✅ 性能优化：高并发处理，支持多分片并行消费
✅ 监控友好：详细的日志记录和处理统计
✅ 环境适配：支持开发/生产环境的不同配置

📋 适用场景
✅ 支持的AI网关类型

阿里云API网关 + AI服务集成
自建AI网关（需输出标准格式日志到SLS）
支持以下AI服务：通义千问、GPT、Claude等

✅ 支持的日志格式

包含 ai_log 字段的JSON格式日志
必须包含 trace_id、question、answer 等关键字段
支持多轮对话和复杂对话场景

⚠️ 重要前置条件
🔧 AI网关配置要求

必须开启链路追踪：AI网关需要配置将访问日志输出到阿里云SLS

日志格式要求：确保日志包含以下字段：
{
  "trace_id": "唯一追踪ID",
  "question": "用户输入",
  "answer": "AI回复", 
  "ai_log": "{JSON格式的AI服务详细信息}",
  "response_code": "HTTP状态码",
  "duration": "请求耗时"
}


SLS Logstore配置：确保已创建对应的Project和Logstore


🏗️ 基础设施要求

阿里云SLS：已配置的项目和日志库
Langfuse实例：可访问的Langfuse服务
Docker环境：Docker 20.10+ 和 Docker Compose（可选）
网络连通性：确保容器可以访问阿里云SLS和Langfuse服务

🚀 快速开始
1️⃣ 克隆项目
git clone https://github.com/your-username/sls-to-langfuse.git
cd sls-to-langfuse

2️⃣ 配置环境变量
复制并编辑配置文件：
cp .env.example .env
vim .env

关键配置说明：
# ======== 阿里云SLS配置 ========
ALIYUN_ENDPOINT=cn-shanghai.log.aliyuncs.com  # 根据你的区域调整
ALIYUN_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID       # 阿里云访问密钥
ALIYUN_ACCESS_KEY_SECRET=YOUR_ACCESS_SECRET   # 阿里云访问密钥
ALIYUN_PROJECT_NAME=your-sls-project          # SLS项目名称
ALIYUN_LOGSTORE_NAME=your-logstore            # SLS日志库名称
ALIYUN_CONSUMER_GROUP_NAME=langfuse-consumer-v1  # 消费组名称（自定义）

# ======== Langfuse配置 ========
LANGFUSE_HOST=https://your-langfuse-domain.com  # Langfuse服务地址
LANGFUSE_PUBLIC_KEY=pk-your-public-key          # Langfuse公钥
LANGFUSE_SECRET_KEY=sk-your-secret-key          # Langfuse私钥
LANGFUSE_SDK_TIMEOUT=30                         # SDK超时时间

# ======== 应用配置 ========
TZ=Asia/Shanghai          # 时区设置
LOG_FORMAT=human          # 日志格式：human(开发) / json(生产)

3️⃣ 一键部署
# 确保脚本可执行
chmod +x deploy.sh

# 部署服务
./deploy.sh

4️⃣ 验证运行
# 查看实时日志
docker logs -f sls_processor_instance

# 检查容器状态
docker ps | grep sls_processor

🔧 详细配置说明
📁 环境变量完整列表



变量名
必需
默认值
说明



ALIYUN_ENDPOINT
✅
无
阿里云SLS服务端点


ALIYUN_ACCESS_KEY_ID
✅
无
阿里云访问密钥ID


ALIYUN_ACCESS_KEY_SECRET
✅
无
阿里云访问密钥


ALIYUN_PROJECT_NAME
✅
无
SLS项目名称


ALIYUN_LOGSTORE_NAME
✅
无
SLS日志库名称


ALIYUN_CONSUMER_GROUP_NAME
✅
无
消费组名称


LANGFUSE_HOST
✅
无
Langfuse服务地址


LANGFUSE_PUBLIC_KEY
✅
无
Langfuse公钥


LANGFUSE_SECRET_KEY
✅
无
Langfuse私钥


LANGFUSE_SDK_TIMEOUT
❌
30
SDK超时时间(秒)


TZ
❌
UTC
容器时区


LOG_FORMAT
❌
human
日志格式


🏷️ 消费组名称说明

⚠️ 重要：ALIYUN_CONSUMER_GROUP_NAME 决定了消费进度的保存位置。

相同名称 = 继承之前的消费进度
不同名称 = 重新开始消费（可能导致重复处理）


建议命名规范：
# 开发环境
ALIYUN_CONSUMER_GROUP_NAME=langfuse-consumer-dev

# 测试环境  
ALIYUN_CONSUMER_GROUP_NAME=langfuse-consumer-test

# 生产环境
ALIYUN_CONSUMER_GROUP_NAME=langfuse-consumer-prod

🐳 Docker镜像说明
📦 镜像源配置
本项目使用华为云镜像源以提高国内用户的下载速度：
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/python:3.11-slim

如需使用官方镜像，请修改 Dockerfile：
# 官方镜像（国外网络环境）
FROM python:3.11-slim

🔄 自定义构建
# 构建自定义镜像
docker build -t your-registry/sls-to-langfuse:latest .

# 推送到私有仓库
docker push your-registry/sls-to-langfuse:latest

📊 监控和运维
📈 关键指标监控
服务运行时会输出以下关键指标：
# 成功处理的日志
✅ 发送成功: Trace [ bc4f12c039b76993... ] | API [ qwen-vl@_origin_@_reserved_ ]

# 分片状态
👍 分片 0 的生产者已启动
💾 分片 0 的检查点已成功提交

# 错误信息
❌ 发送失败 (尝试 1/3): Trace [ abc123... ]
🚨 发送最终失败，已放弃: Trace [ def456... ]

🔍 故障排除
问题1：容器启动失败
# 检查环境变量
docker run --rm --env-file .env sls-to-langfuse-service env

# 检查网络连通性
docker run --rm --env-file .env sls-to-langfuse-service ping cn-shanghai.log.aliyuncs.com

问题2：无法消费日志
# 检查SLS权限
# 确保Access Key具有以下权限：
# - log:GetConsumerGroupCheckPoint
# - log:UpdateConsumerGroup
# - log:ConsumerGroupUpdateCheckPoint
# - log:ListConsumerGroup
# - log:PullLogs

问题3：Langfuse连接失败
# 测试Langfuse连接
curl -X GET "${LANGFUSE_HOST}/api/public/health"

# 检查密钥配置
# 确保Public Key和Secret Key匹配且有效

问题4：重复处理日志
# 原因：消费组名称变更或检查点丢失
# 解决：保持消费组名称一致，检查SLS控制台的消费组状态

📋 运维命令
# 查看服务状态
docker ps | grep sls_processor

# 重启服务
./deploy.sh

# 查看详细日志
docker logs --tail 100 -f sls_processor_instance

# 进入容器调试
docker exec -it sls_processor_instance /bin/bash

# 清理旧镜像
docker image prune -f

# 停止服务
docker stop sls_processor_instance
docker rm sls_processor_instance

🔒 安全注意事项

敏感信息保护：

不要将 .env 文件提交到版本控制
定期轮换阿里云Access Key和Langfuse密钥
使用最小权限原则配置IAM


网络安全：

确保容器运行在安全的网络环境中
考虑使用VPN或专线连接云服务


数据隐私：

注意AI对话内容可能包含敏感信息
确保Langfuse部署符合数据合规要求



🛠️ 开发指南
🔧 本地开发
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export $(cat .env | xargs)

# 运行服务
python -m sls_processor.main

🧪 测试
# 单元测试
python -m pytest tests/

# 集成测试
python -m pytest tests/integration/

# 性能测试
python -m pytest tests/performance/

📝 代码结构
sls_processor/
├── main.py          # 主程序入口
├── consumer.py      # SLS消费者逻辑
├── processor.py     # 数据处理和转换
└── models/          # 数据模型定义
    ├── sls_log.py
    └── langfuse_data.py

🤝 贡献指南
欢迎提交Issue和Pull Request！

Fork 本仓库
创建特性分支：git checkout -b feature/amazing-feature
提交变更：git commit -m 'Add amazing feature'
推送分支：git push origin feature/amazing-feature
创建Pull Request

📄 许可证
本项目采用 MIT 许可证 - 查看 LICENSE 文件了解详情。
🆘 获得帮助

📖 项目文档
🐛 报告Bug
💬 讨论区
📧 联系我们：your-email@domain.com


⭐ 如果这个项目对你有帮助，请给我们一个Star！
