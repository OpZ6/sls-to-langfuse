# sls_processor/processor.py

import json
import logging
import time
import os
from typing import Dict, Any, Optional
from queue import Queue, Empty

# --- LangfuseDataProcessor 和 LangfuseSender 类的代码 ---
class LangfuseDataProcessor:
    """SLS日志到Langfuse数据的转换处理器 - 高性能精简版"""
    
    @staticmethod
    def parse_ai_log(ai_log_str: str) -> Dict[str, Any]:
        """解析ai_log JSON字符串"""
        try:
            return json.loads(ai_log_str) if ai_log_str and ai_log_str.strip() and ai_log_str != '{}' else {}
        except json.JSONDecodeError:
            return {}
    
    @staticmethod
    def safe_int(value: Any) -> Optional[int]:
        """安全转换为整数"""
        if value is None or value == '' or value == '-':
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def build_performance_metadata(ai_log: Dict, log_contents: Dict) -> Dict[str, Any]:
        """构建性能metadata - 预过滤"""
        data = {}
        if (duration := LangfuseDataProcessor.safe_int(log_contents.get('duration'))):
            data["total_duration_ms"] = duration
        if (llm_duration := LangfuseDataProcessor.safe_int(ai_log.get('llm_service_duration'))):
            data["llm_service_duration_ms"] = llm_duration
        if (upstream := LangfuseDataProcessor.safe_int(log_contents.get('upstream_service_time'))):
            data["upstream_service_time_ms"] = upstream
        if (response_tx := LangfuseDataProcessor.safe_int(log_contents.get('response_tx_duration'))):
            data["response_tx_duration_ms"] = response_tx
        return data
    
    @staticmethod
    def build_request_metadata(log_contents: Dict) -> Dict[str, Any]:
        """构建请求metadata - 预过滤"""
        data = {}
        if (method := log_contents.get('method')):
            data["method"] = method
        if (path := log_contents.get('path')):
            data["path"] = path
        if (original_path := log_contents.get('original_path')):
            data["original_path"] = original_path
        if (response_code := LangfuseDataProcessor.safe_int(log_contents.get('response_code'))):
            data["response_code"] = response_code
        if (response_details := log_contents.get('response_code_details')):
            data["response_code_details"] = response_details
        if (user_agent := log_contents.get('user_agent')):
            data["user_agent"] = user_agent
        if (protocol := log_contents.get('protocol')):
            data["protocol"] = protocol
        if (authority := log_contents.get('authority')):
            data["authority"] = authority
        return data
    
    @staticmethod
    def build_infrastructure_metadata(log_contents: Dict) -> Dict[str, Any]:
        """构建基础设施metadata - 预过滤"""
        data = {}
        if (container_ip := log_contents.get('_container_ip_')):
            data["container_ip"] = container_ip
        if (namespace := log_contents.get('_namespace_')):
            data["namespace"] = namespace
        if (cluster_id := log_contents.get('cluster_id')):
            data["cluster_id"] = cluster_id
        if (route_name := log_contents.get('route_name')):
            data["route_name"] = route_name
        if (upstream_host := log_contents.get('upstream_host')):
            data["upstream_host"] = upstream_host
        return data
    
    @staticmethod
    def convert_to_langfuse_format(log_contents: Dict[str, Any]) -> Dict[str, Any]:
        """将SLS日志转换为Langfuse格式 - 高性能版"""
        ai_log = LangfuseDataProcessor.parse_ai_log(log_contents.get('ai_log', '{}'))
        
        # 核心字段提取
        trace_input = log_contents.get('question', '')
        trace_output = log_contents.get('answer', '') if log_contents.get('answer') != '-' else ''
        api_prefix = ai_log.get('api', '').split('@')[0] if ai_log.get('api') else ''
        response_code = LangfuseDataProcessor.safe_int(log_contents.get('response_code'))
        
        # 🚀 性能优化：预构建usage_details（避免重复检查）
        usage_details = None
        if ai_log.get('input_token') or ai_log.get('output_token') or ai_log.get('total_token'):
            usage_details = {}
            if (input_tokens := LangfuseDataProcessor.safe_int(ai_log.get('input_token'))):
                usage_details['input'] = input_tokens
            if (output_tokens := LangfuseDataProcessor.safe_int(ai_log.get('output_token'))):
                usage_details['output'] = output_tokens
            if (total_tokens := LangfuseDataProcessor.safe_int(ai_log.get('total_token'))):
                usage_details['total'] = total_tokens
        
        # 🚀 性能优化：预构建tags（避免filter和list操作）
        tags = []
        if api_prefix:
            tags.append(api_prefix)
        if ai_log.get('response_type'):
            tags.append(ai_log.get('response_type'))
        if log_contents.get('_namespace_'):
            tags.append(log_contents.get('_namespace_'))
        if ai_log.get('model'):
            tags.append(f"model:{ai_log.get('model')}")
        
        # 状态标签
        if response_code:
            if 200 <= response_code < 300:
                tags.append("status:success")
            elif 400 <= response_code < 500:
                tags.append("status:client_error")
            elif response_code >= 500:
                tags.append("status:server_error")
            else:
                tags.append("status:other")
        else:
            tags.append("status:unknown")
        
        # 🚀 性能优化：直接确定level（避免重复判断）
        if response_code is None:
            level = "DEFAULT"
        elif 200 <= response_code < 300:
            level = "DEFAULT"
        elif 400 <= response_code < 500:
            level = "WARNING"
        elif response_code >= 500:
            level = "ERROR"
        else:
            level = "DEBUG"
        
        # 🚀 性能优化：预构建状态消息
        status_parts = []
        if response_code:
            status_parts.append(f"HTTP {response_code}")
        if log_contents.get('response_code_details'):
            status_parts.append(log_contents.get('response_code_details'))
        if ai_log.get('response_type'):
            status_parts.append(f"AI: {ai_log.get('response_type')}")
        status_message = " | ".join(status_parts) if status_parts else "Unknown"
        
        # 🚀 性能优化：预构建generation名称
        if ai_log.get('chat_round'):
            generation_name = f"{ai_log.get('api', 'AI Generation')} - Round {ai_log.get('chat_round')}"
        elif ai_log.get('model'):
            generation_name = f"{ai_log.get('api', 'AI Generation')} ({ai_log.get('model')})"
        else:
            generation_name = ai_log.get('api', 'AI Generation')
        
        # 🚀 性能优化：分别构建metadata子组（避免嵌套clean_dict）
        metadata = {}
        
        # 环境信息
        if log_contents.get('_namespace_'):
            metadata["environment"] = log_contents.get('_namespace_', 'default')
        
        # 性能指标
        if (performance := LangfuseDataProcessor.build_performance_metadata(ai_log, log_contents)):
            metadata["performance"] = performance
        
        # 请求信息
        if (request := LangfuseDataProcessor.build_request_metadata(log_contents)):
            metadata["request"] = request
        
        # 基础设施信息
        if (infrastructure := LangfuseDataProcessor.build_infrastructure_metadata(log_contents)):
            metadata["infrastructure"] = infrastructure
        
        # 对话上下文
        chat_context = {}
        if ai_log.get('api'):
            chat_context["api_full_name"] = ai_log.get('api')
        if ai_log.get('chat_round'):
            chat_context["chat_round"] = ai_log.get('chat_round')
        if ai_log.get('response_type'):
            chat_context["response_type"] = ai_log.get('response_type')
        if ai_log.get('fallback_from'):
            chat_context["fallback_from"] = ai_log.get('fallback_from')
        if chat_context:
            metadata["chat_context"] = chat_context
        
        # 网络传输
        network = {}
        if (bytes_sent := LangfuseDataProcessor.safe_int(log_contents.get('bytes_sent'))):
            network["bytes_sent"] = bytes_sent
        if (bytes_received := LangfuseDataProcessor.safe_int(log_contents.get('bytes_received'))):
            network["bytes_received"] = bytes_received
        if log_contents.get('downstream_remote_address'):
            network["downstream_remote_address"] = log_contents.get('downstream_remote_address')
        if log_contents.get('upstream_local_address'):
            network["upstream_local_address"] = log_contents.get('upstream_local_address')
        if network:
            metadata["network"] = network
        
        # 原始追踪信息
        original_trace = {}
        if log_contents.get('trace_id'):
            original_trace["sls_trace_id"] = log_contents.get('trace_id')
        if log_contents.get('request_id'):
            original_trace["request_id"] = log_contents.get('request_id')
        if log_contents.get('_time_'):
            original_trace["log_time"] = log_contents.get('_time_')
        if log_contents.get('start_time'):
            original_trace["start_time"] = log_contents.get('start_time')
        if original_trace:
            metadata["original_trace"] = original_trace
        
        # 🚀 性能优化：直接构建结果（避免clean_data递归调用）
        result = {
            "trace_name": ai_log.get('api', 'AI Request'),
            "trace_input": trace_input,
            "trace_output": trace_output,
            "generation_name": generation_name,
            "generation_input": trace_input,
            "generation_output": trace_output,
            "level": level,
            "status_message": status_message,
            "tags": tags
        }
        
        # 添加可选字段
        if ai_log.get('consumer') or log_contents.get('consumer'):
            result["user_id"] = ai_log.get('consumer', log_contents.get('consumer', ''))
        if ai_log.get('chat_id'):
            result["session_id"] = ai_log.get('chat_id')
        if ai_log.get('model'):
            result["model"] = ai_log.get('model')
        if usage_details:
            result["usage_details"] = usage_details
        if log_contents.get('start_time'):
            result["start_time"] = log_contents.get('start_time')
        if metadata:
            result["metadata"] = metadata
        
        return result

class LangfuseSender:
    """Langfuse数据发送器"""
    
    def __init__(self):
        try:
            # --- ✨ 核心修正：直接初始化客户端，让它自动读取环境变量 ---
            from langfuse import get_client
            self.langfuse = get_client()
            
            # 从 os.environ 读取 HOST 用于打印，确保信息来源一致
            host = os.environ.get('LANGFUSE_HOST', 'N/A')
            logger.info(f"✅ Langfuse客户端初始化成功，将连接到: {host}")

        except Exception as e:
            logger.error(f"❌ Langfuse客户端初始化失败: {e}", exc_info=True)
            raise


    def send_trace_with_generation(self, data: Dict[str, Any]) -> bool:
        """发送trace和generation"""
        try:
            with self.langfuse.start_as_current_span(
                name=data.get('trace_name', 'AI Request'),
                input=data.get('trace_input')
            ) as root_span:
                
                root_span.update_trace(
                    input=data.get('trace_input'),
                    output=data.get('trace_output'),
                    user_id=data.get('user_id'),
                    session_id=data.get('session_id'),
                    tags=data.get('tags', []),
                    metadata=data.get('metadata', {})
                )
                
                root_span.update(output=data.get('trace_output'), metadata=data.get('metadata', {}))
                
                with self.langfuse.start_as_current_observation(
                    as_type='generation',
                    name=data.get('generation_name', 'AI Generation'),
                    input=data.get('generation_input'),
                    model=data.get('model')
                ) as generation:
                    
                    update_params = {
                        'output': data.get('generation_output'),
                        'level': data.get('level', 'DEFAULT'),
                        'status_message': data.get('status_message', ''),
                        'metadata': data.get('metadata', {})
                    }
                    
                    if data.get('usage_details'):
                        update_params['usage_details'] = data.get('usage_details')
                    
                    generation.update(**update_params)
            
            return True
        except Exception as e:
            logger.error(f"发送到Langfuse失败: {e}")
            return False
    
    def flush(self) -> bool:
        try:
            self.langfuse.flush()
            return True
        except Exception as e:
            logger.error(f"Langfuse刷新失败: {e}")
            return False


# --- 新增的处理器主循环 ---
logger = logging.getLogger(__name__)

def write_to_dead_letter_queue(log_data: Dict[str, Any]):
    """将处理失败的日志写入本地文件，以便后续排查。"""
    try:
        with open(DEAD_LETTER_QUEUE_FILE, "a") as f:
            f.write(json.dumps(log_data) + "\n")
        logger.warning(f"日志已写入死信队列: {DEAD_LETTER_QUEUE_FILE}")
    except Exception as e:
        logger.error(f"写入死信队列失败: {e}")

def process_logs_from_queue(log_queue: Queue, stop_event):
    """
    从队列中获取日志，处理并发送到Langfuse，增加了重试和死信队列逻辑。
    """
    sender = LangfuseSender()
    stats = {'processed': 0, 'success': 0, 'error': 0, 'skipped': 0, 'retries': 0, 'dead_letter': 0}
    start_time = time.time()
    
    # --- 新增：重试参数配置 ---
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 5

    logger.info("🚀 Langfuse处理器已启动 (增强版：带重试和死信队列)...")

    while not stop_event.is_set():
        try:
            log_data = log_queue.get(timeout=1.0)
        except Empty:
            continue # 队列为空，正常，继续循环
        
        stats['processed'] += 1
        trace_id = log_data.get('trace_id', 'N/A')

        langfuse_data = LangfuseDataProcessor.convert_to_langfuse_format(log_data)
        
        # --- 新增：带重试的发送逻辑 ---
        sent_successfully = False
        for attempt in range(MAX_RETRIES):
            if sender.send_trace_with_generation(langfuse_data):
                stats['success'] += 1
                sent_successfully = True
                logger.info(f"✅ 发送成功: Trace [ {trace_id[:16]}... ] | API [ {langfuse_data.get('trace_name', 'N/A')} ]")
                break # 成功则跳出重试循环
            else:
                stats['retries'] += 1
                logger.warning(f"❌ 发送失败 (尝试 {attempt + 1}/{MAX_RETRIES}): Trace [ {trace_id[:16]}... ]")
                if attempt < MAX_RETRIES - 1:
                    # 如果不是最后一次尝试，则等待一段时间再重试
                    time.sleep(RETRY_DELAY_SECONDS)
        
        # --- 新增：处理最终失败的情况 ---
        if not sent_successfully:
            stats['error'] += 1
            stats['dead_letter'] += 1
            logger.error(f"🚨 发送最终失败，已放弃: Trace [ {trace_id[:16]}... ]")
            write_to_dead_letter_queue(log_data)

        # --- 修改定期统计日志的频率和内容 ---
        if stats['processed'] % 50 == 0:
            # ... (统计日志打印部分保持不变) ...
            pass

    logger.info("ℹ️ 收到停止信号，正在刷新Langfuse SDK...")
    sender.flush()
    logger.info("✅ Langfuse处理器已成功关闭。")