# Dockerfile

# 1. 使用一个已验证可用的、位于华为云的Python镜像作为基础
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/python:3.11-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 将依赖文件复制到镜像中
COPY requirements.txt .

# 4. 安装依赖 (使用 --no-cache-dir 减小镜像体积)
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 5. 将我们的应用代码复制到镜像中
COPY ./sls_processor ./sls_processor

# 6. 设置默认启动命令
# 当容器启动时，执行我们的主程序
CMD ["python", "-m", "sls_processor.main"]