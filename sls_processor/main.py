# sls_processor/main.py
    
import logging
import os
import threading
import time
from queue import Queue

# --- ✨ 新增: 加载环境变量 ---
from dotenv import load_dotenv
load_dotenv() # 会自动寻找项目根目录的 .env 文件并加载

from aliyun.log import LogClient
from aliyun.log.consumer import CursorPosition, LogHubConfig

# --- ✨ 修改: 从内部模块导入 ---
from .consumer import start_sls_consumer_worker
from .processor import process_logs_from_queue

# --- 配置区 (集中管理) ---
# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 阿里云 SLS 配置
ENDPOINT = os.getenv("ALIYUN_ENDPOINT")
ACCESS_KEY_ID = os.getenv("ALIYUN_ACCESS_KEY_ID")
ACCESS_KEY_SECRET = os.getenv("ALIYUN_ACCESS_KEY_SECRET")
PROJECT_NAME = os.getenv("ALIYUN_PROJECT_NAME")
LOGSTORE_NAME = os.getenv("ALIYUN_LOGSTORE_NAME")
CONSUMER_GROUP_NAME = os.getenv("ALIYUN_CONSUMER_GROUP_NAME")
CONSUMER_NAME_PREFIX = 'realtime-processor'

# Langfuse 配置 (您的第二个脚本中的配置)
os.environ['LANGFUSE_SECRET_KEY'] = "sk-lf-db0fe111-d13b-4bdc-9937-ee8f06985d6e"
os.environ['LANGFUSE_PUBLIC_KEY'] = "pk-lf-c4d46db6-3ab6-41e6-8620-a38684a8d794" 
os.environ['LANGFUSE_HOST'] = "http://47.100.30.138:3000"

def ensure_consumer_group(client, project, logstore, group_name):
    """检查并创建消费组，避免程序启动因已存在而出错。"""
    try:
        client.create_consumer_group(project, logstore, group_name, timeout=300)
        logger.info(f"消费组 '{group_name}' 创建成功。")
    except Exception as e:
        if "ConsumerGroupAlreadyExist" in str(e):
            logger.info(f"消费组 '{group_name}' 已存在，将直接使用。")
        else:
            logger.error(f"创建消费组 '{group_name}' 失败: {e}")
            raise

def main():
    logger.info("🚀 应用启动...")

    # 1. 创建用于线程间通信的共享队列
    log_queue = Queue(maxsize=10000)  # 设置最大容量以防止内存无限增长

    # 2. 创建用于通知子线程停止的事件
    stop_event = threading.Event()

    # 3. 准备SLS消费者配置
    consumer_name = f"{CONSUMER_NAME_PREFIX}-{int(time.time())}"
    logger.info(f"本次消费者名称: {consumer_name}")
    
    client = LogClient(ENDPOINT, ACCESS_KEY_ID, ACCESS_KEY_SECRET)
    ensure_consumer_group(client, PROJECT_NAME, LOGSTORE_NAME, CONSUMER_GROUP_NAME)
    
    config = LogHubConfig(
        ENDPOINT, ACCESS_KEY_ID, ACCESS_KEY_SECRET,
        PROJECT_NAME, LOGSTORE_NAME, CONSUMER_GROUP_NAME,
        consumer_name, cursor_position=CursorPosition.END_CURSOR
    )

    # 4. 在后台线程中启动SLS消费者 (生产者)
    sls_worker = start_sls_consumer_worker(config, log_queue)
    
    # 5. 在另一个后台线程中启动Langfuse处理器 (消费者)
    processor_thread = threading.Thread(
        target=process_logs_from_queue,
        args=(log_queue, stop_event),
        name="LangfuseProcessorThread"
    )
    processor_thread.start()

    # 6. 主线程保持运行，并等待用户中断 (Ctrl+C)
    try:
        while True:
            time.sleep(1)
            if not processor_thread.is_alive():
                logger.warning("Langfuse处理线程似乎已停止，正在退出应用...")
                break
    except KeyboardInterrupt:
        logger.info("🛑 收到用户中断信号 (Ctrl+C)，开始优雅关闭...")
    finally:
        # 优雅停机流程
        logger.info("1/2 - 正在停止SLS消费者...")
        sls_worker.shutdown()
        
        logger.info("2/2 - 正在通知Langfuse处理器完成剩余任务并停止...")
        stop_event.set()
        processor_thread.join(timeout=30) # 等待处理器线程最多30秒

        if processor_thread.is_alive():
            logger.warning("Langfuse处理器在超时后仍未退出。")

        logger.info("✅ 应用已成功关闭。")

if __name__ == "__main__":
    main()