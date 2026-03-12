#!/usr/bin/env python3
"""
Agent Chat Server - 独立的 Agent 对话服务器

使用方法:
    python server.py
    
    然后访问 http://localhost:8889
"""

import sys
import os
import asyncio
import json
import uuid
import threading
from datetime import datetime
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS

# 添加 agent 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent'))

app = Flask(__name__)
CORS(app)

# 配置
PORT = 8889
AGENT_DIR = os.path.join(os.path.dirname(__file__), '..', 'agent')

# 全局变量 - 使用线程锁保护
agent_lock = threading.Lock()
tester = None


async def init_agent():
    """初始化 Agent"""
    global tester
    
    try:
        from test_agent_rag_v8_1 import DirectAgentTester
        
        print("正在初始化 Agent...")
        tester = DirectAgentTester(
            enable_logging=True, 
            session_name=f"web_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        await tester.initialize()
        print("Agent 初始化完成!")
        return True
        
    except Exception as e:
        print(f"Agent 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_async_in_new_loop(coro):
    """在新的事件循环中运行异步函数"""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.route('/')
def index():
    """首页"""
    return send_from_directory('.', 'index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """普通对话接口（非流式）"""
    global tester
    
    # 使用线程锁确保只有一个请求在操作 Agent
    with agent_lock:
        if tester is None:
            success = run_async_in_new_loop(init_agent())
            if not success:
                return jsonify({
                    'success': False,
                    'error': 'Agent 初始化失败'
                }), 500
        
        data = request.json
        query = data.get('message', '').strip()
        
        if not query:
            return jsonify({
                'success': False,
                'error': '消息不能为空'
            }), 400
        
        try:
            # 在新的事件循环中运行
            result = run_async_in_new_loop(tester.query(query))
            
            # 处理引用去重
            citations = result.get('citations', [])
            seen_titles = set()
            unique_citations = []
            for c in citations:
                title = c.get('doc_title', 'Unknown')
                if title not in seen_titles:
                    seen_titles.add(title)
                    unique_citations.append(c)
            
            return jsonify({
                'success': True,
                'data': {
                    'id': str(uuid.uuid4()),
                    'role': 'assistant',
                    'content': result.get('answer', ''),
                    'agent_used': result.get('agent_used', 'unknown'),
                    'processing_time': result.get('processing_time', 0),
                    'classification': result.get('classification', {}),
                    'citations': unique_citations,
                    'qc_report': result.get('qc_report', {}),
                    'timestamp': datetime.now().isoformat()
                }
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """流式对话接口（打字机效果）"""
    global tester
    
    # 在请求上下文外读取数据
    data = request.json
    query = data.get('message', '').strip() if data else ''
    
    def generate():
        global tester
        
        # 使用线程锁
        with agent_lock:
            if tester is None:
                success = run_async_in_new_loop(init_agent())
                if not success:
                    yield f"data: {json.dumps({'error': 'Agent 初始化失败'}, ensure_ascii=False)}\n\n"
                    return
            
            if not query:
                yield f"data: {json.dumps({'error': '消息不能为空'}, ensure_ascii=False)}\n\n"
                return
            
            try:
                # 在新的事件循环中运行
                result = run_async_in_new_loop(tester.query(query))
                
                answer = result.get('answer', '')
                
                # 模拟打字机效果，按句子分割
                import re
                sentences = re.split(r'([。！？.!?]\s*)', answer)
                
                current_text = ""
                for i, sentence in enumerate(sentences):
                    if sentence:
                        current_text += sentence
                        data = {
                            'id': str(uuid.uuid4()),
                            'role': 'assistant',
                            'content': current_text,
                            'done': False
                        }
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                
                # 发送最终结果（包含完整元信息）
                citations = result.get('citations', [])
                seen_titles = set()
                unique_citations = []
                for c in citations:
                    title = c.get('doc_title', 'Unknown')
                    if title not in seen_titles:
                        seen_titles.add(title)
                        unique_citations.append(c)
                
                final_data = {
                    'id': str(uuid.uuid4()),
                    'role': 'assistant',
                    'content': answer,
                    'done': True,
                    'agent_used': result.get('agent_used', 'unknown'),
                    'processing_time': result.get('processing_time', 0),
                    'classification': result.get('classification', {}),
                    'citations': unique_citations,
                    'qc_report': result.get('qc_report', {}),
                    'timestamp': datetime.now().isoformat()
                }
                yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/health')
def health():
    """健康检查"""
    global tester
    with agent_lock:
        return jsonify({
            'status': 'ok',
            'agent_ready': tester is not None and tester._initialized
        })


@app.route('/api/reset', methods=['POST'])
def reset():
    """重置 Agent"""
    global tester
    
    with agent_lock:
        if tester:
            try:
                run_async_in_new_loop(tester.close())
            except:
                pass
            tester = None
    
    return jsonify({
        'success': True,
        'message': 'Agent 已重置'
    })


if __name__ == '__main__':
    print("=" * 60)
    print("🤖 Agent Chat Server")
    print("=" * 60)
    print(f"服务地址: http://localhost:{PORT}")
    print(f"Agent 目录: {os.path.abspath(AGENT_DIR)}")
    print("=" * 60)
    print("按 Ctrl+C 停止服务")
    print()
    
    # 预初始化 Agent（可选，但建议预初始化以避免第一次请求慢）
    print("正在预初始化 Agent（首次加载可能需要一些时间）...")
    success = run_async_in_new_loop(init_agent())
    if success:
        print("✅ Agent 已就绪")
    else:
        print("⚠️ Agent 初始化失败，将在首次请求时重试")
    
    print()
    
    # 使用单线程模式避免事件循环冲突
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=False)
