#!/bin/bash

# deploy.sh
# 一个用于在服务器上自动拉取更新、重建并重启Docker容器的脚本。

# --- 配置 ---
# 设置镜像和容器的名称，方便管理
IMAGE_NAME="sls-to-langfuse-service"
CONTAINER_NAME="sls_processor_instance"
ENV_FILE="./.env" # 指定你的env文件路径

# set -e: 脚本中的任何命令失败，则立即退出。
# 这可以防止在git pull失败或docker build失败的情况下，还继续运行一个旧的或损坏的服务。
set -e

# --- 部署流程 ---

# 1. 拉取最新的代码
echo "🔄 正在从GitHub拉取最新代码..."
git pull origin main # 假设你的主分支是 main

# 2. 使用最新的代码重新构建Docker镜像
echo "🛠️ 正在构建新的Docker镜像 (tag: $IMAGE_NAME)..."
docker build -t $IMAGE_NAME .

# 3. 检查并清理旧容器
if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo "🛑 正在停止旧的容器..."
    docker stop $CONTAINER_NAME
fi

if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
    echo "🗑️ 正在移除旧的容器..."
    docker rm $CONTAINER_NAME
fi

# 4. 启动新容器 - 完全依赖.env文件
echo "🚀 正在启动新容器..."
docker run -d \
    --name $CONTAINER_NAME \
    --env-file $ENV_FILE \
    --restart unless-stopped \
    $IMAGE_NAME
    
echo "✅ 部署完成！服务 '$CONTAINER_NAME' 已成功启动。"
echo "   使用 'docker logs -f $CONTAINER_NAME' 查看实时日志。"