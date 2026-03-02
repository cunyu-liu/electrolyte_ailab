#!/usr/bin/env python3
"""测试RAG服务是否正常工作"""
import asyncio
import sys
sys.path.insert(0, '/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent')

from agent_rag_v8 import RAGService, LLMService, LLM_MODEL_PATH

async def test():
    print("=" * 60)
    print("测试RAG服务")
    print("=" * 60)
    
    # 初始化LLM
    print("\n1. 初始化LLM服务...")
    llm = LLMService(LLM_MODEL_PATH)
    
    # 初始化RAG
    print("\n2. 初始化RAG服务...")
    rag = RAGService(llm)
    
    # 检查Milvus连接
    print(f"\n3. Milvus连接状态: {'✓ 已连接' if rag.milvus_collection else '✗ 未连接'}")
    print(f"   ES连接状态: {'✓ 已连接' if rag.es_client else '✗ 未连接'}")
    
    if rag.milvus_collection is None:
        print("\n❌ Milvus未连接，无法进行检索")
        print("   请检查: milvus服务是否启动 (docker ps | grep milvus)")
        return
    
    # 测试检索
    query = "锂离子电池高电压电解液添加剂"
    print(f"\n4. 测试检索: {query}")
    
    try:
        findings = await rag.deep_research(query, depth=2, breadth=3)
        print(f"   ✓ 找到 {len(findings)} 条结果")
        
        if findings:
            print(f"\n5. 第一条结果预览:")
            print(f"   内容: {findings[0].content[:200]}...")
            print(f"   引用数: {len(findings[0].citations)}")
        else:
            print("\n   ⚠️ 没有找到任何结果")
            
    except Exception as e:
        print(f"   ❌ 检索失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
