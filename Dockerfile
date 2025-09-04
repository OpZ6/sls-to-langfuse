# Dockerfile

# 1. 使用官方的、轻量的Python基础镜像
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/python:3.11-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 将依赖文件复制到镜像中
COPY requirements.txt .

# 4. 安装依赖 (使用 --no-cache-dir 减小镜像体积)
# 这一步单独执行可以利用Docker的层缓存机制，当代码改变但依赖不变时，无需重新安装
RUN pip install --no-cache-dir -r requirements.txt

# 5. 将我们的应用代码复制到镜像中
COPY ./sls_processor ./sls_processor

# 6. 设置默认启动命令
# 当容器启动时，执行我们的主程序
CMD ["python", "-m", "sls_processor.main"]