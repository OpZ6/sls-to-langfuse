# sls_processor/sls_consumer.py

import logging
import time
from queue import Queue

# --- ✨ 核心修正：从正确的子模块导入 ---
from aliyun.log import LogClient
from aliyun.log.consumer import ConsumerWorker, ConsumerProcessorBase, LogHubConfig, CursorPosition


# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LogQueueProducer(ConsumerProcessorBase):
    """
    一个将SLS日志放入共享队列的消费者处理器。
    """
    def __init__(self, log_queue: Queue):
        super(LogQueueProducer, self).__init__()
        self.log_queue = log_queue
        self.shard_id = None
        logger.info("✔️ 日志生产者处理器已创建，等待分片分配...")

    def initialize(self, shard):
        self.shard_id = shard
        logger.info(f"👍 分片 {self.shard_id} 的生产者已启动。")

    def process(self, log_groups, check_point_tracker):
        """
        核心处理方法：将有效的trace日志放入队列，并提交检查点。
        """
        try:
            put_count = 0
            for log_group in log_groups.LogGroups:
                for log in log_group.Logs:
                    log_contents = {content.Key: content.Value for content in log.Contents}
                    
                    trace_id = log_contents.get('trace_id', '')
                    if trace_id and trace_id != '-' and len(trace_id) > 10:
                        try:
                            self.log_queue.put(log_contents, block=True, timeout=1) # 使用带超时的阻塞put更安全
                            put_count += 1
                            logger.info(f"📥 捕获日志: Trace [ {trace_id[:16]}... ] 已放入队列")
                        except Exception as e:
                            # 如果队列已满，这里可能会抛出异常
                            logger.error(f"将日志放入队列失败: {e}", exc_info=True)
            
            if put_count > 0:
                logger.debug(f"分片 {self.shard_id}: 本批次 {put_count} 条有效日志已放入队列。当前队列大小: {self.log_queue.qsize()}")
        
        finally:
            # --- ✨ 轻量级重试（不阻塞主流程） ---
            max_retries = 2  # 保持轻量
            for attempt in range(max_retries + 1):
                try:
                    check_point_tracker.save_check_point(True)
                    logger.info(f"💾 分片 {self.shard_id} 的检查点已成功提交 (尝试 {attempt + 1})")
                    break
                except Exception as e:
                    if attempt == max_retries:
                        logger.error(f"🚨 分片 {self.shard_id} 检查点最终失败，已记录: {e}")
                        # 可选：记录到监控系统
                        self._record_checkpoint_failure(self.shard_id, str(e))
                    else:
                        logger.warning(f"⚠️ 分片 {self.shard_id} 检查点重试 {attempt + 1}: {e}")
                        time.sleep(0.5)  # 很短的延迟
            
    def shutdown(self, check_point_tracker):
        logger.info(f"ℹ️ 生产者正在为分片 {self.shard_id} 关闭...")


def start_sls_consumer_worker(config: LogHubConfig, log_queue: Queue):
    """启动并管理ConsumerWorker。"""
    logger.info("🚀 启动 ConsumerWorker...")
    # 通过 lambda 传递队列实例给处理器
    worker = ConsumerWorker(lambda: LogQueueProducer(log_queue), consumer_option=config)
    worker.start(join=False)  # 在后台运行
    logger.info("✅ ConsumerWorker 已在后台线程启动。")
    return worker