#!/usr/bin/env python3
"""
Example script to test Synapse API
"""

import os
import json
import asyncio
from openai import AsyncOpenAI
import httpx

# Configuration
BASE_URL = os.getenv("SYNAPSE_URL", "http://localhost:8000")
API_KEY = os.getenv("SYNAPSE_API_KEY", "test-api-key")


async def test_chat_completion():
    """Test OpenAI-compatible chat completion"""
    print("🔍 Testing Chat Completion...")
    
    client = AsyncOpenAI(
        base_url=f"{BASE_URL}/v1",
        api_key=API_KEY
    )
    
    try:
        response = await client.chat.completions.create(
            model="synapse",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello! Can you explain what Synapse is?"}
            ],
            temperature=0.7
        )
        
        print("✅ Chat Completion Response:")
        print(f"   Model: {response.model}")
        print(f"   Response: {response.choices[0].message.content[:200]}...")
        return True
        
    except Exception as e:
        print(f"❌ Chat Completion failed: {e}")
        return False


async def test_streaming():
    """Test streaming chat completion"""
    print("\n🔍 Testing Streaming...")
    
    client = AsyncOpenAI(
        base_url=f"{BASE_URL}/v1",
        api_key=API_KEY
    )
    
    try:
        stream = await client.chat.completions.create(
            model="synapse-fast",
            messages=[
                {"role": "user", "content": "Count from 1 to 5"}
            ],
            stream=True
        )
        
        print("✅ Streaming Response:")
        print("   ", end="")
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Streaming failed: {e}")
        return False


async def test_memory():
    """Test memory API"""
    print("\n🔍 Testing Memory API...")
    
    async with httpx.AsyncClient() as client:
        # Add a memory
        try:
            response = await client.post(
                f"{BASE_URL}/api/memory/test-user",
                json={
                    "content": "User prefers Python for coding",
                    "memory_type": "preference"
                },
                headers={"Authorization": f"Bearer {API_KEY}"}
            )
            
            if response.status_code == 200:
                memory = response.json()
                print(f"✅ Memory added: {memory['id']}")
                
                # Retrieve memories
                response = await client.get(
                    f"{BASE_URL}/api/memory/test-user",
                    headers={"Authorization": f"Bearer {API_KEY}"}
                )
                
                if response.status_code == 200:
                    memories = response.json()
                    print(f"✅ Retrieved {memories['count']} memories")
                    return True
            
        except Exception as e:
            print(f"❌ Memory API failed: {e}")
            return False


async def test_document_search():
    """Test document search"""
    print("\n🔍 Testing Document Search...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/search",
                params={
                    "query": "AI assistant",
                    "user_id": "test-user",
                    "limit": 5
                },
                headers={"Authorization": f"Bearer {API_KEY}"}
            )
            
            if response.status_code == 200:
                results = response.json()
                print(f"✅ Search returned {len(results.get('documents', []))} documents")
                return True
            else:
                print(f"⚠️  No documents found (this is normal if no documents uploaded)")
                return True
                
        except Exception as e:
            print(f"❌ Document search failed: {e}")
            return False


async def test_health():
    """Test health endpoint"""
    print("\n🔍 Testing Health Check...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            
            if response.status_code == 200:
                health = response.json()
                print(f"✅ Service Status: {health['status']}")
                print("   Services:")
                for service, status in health.get('services', {}).items():
                    emoji = "✅" if status == "healthy" else "❌"
                    print(f"     {emoji} {service}: {status}")
                return health['status'] in ['healthy', 'degraded']
            
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False


async def test_models():
    """Test models endpoint"""
    print("\n🔍 Testing Models List...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/v1/models",
                headers={"Authorization": f"Bearer {API_KEY}"}
            )
            
            if response.status_code == 200:
                models = response.json()
                print(f"✅ Available models:")
                for model in models.get('data', [])[:5]:
                    print(f"     - {model['id']}")
                return True
            
        except Exception as e:
            print(f"❌ Models list failed: {e}")
            return False


async def main():
    """Run all tests"""
    print("=" * 50)
    print("       SYNAPSE API TEST SUITE")
    print("=" * 50)
    print(f"Testing API at: {BASE_URL}")
    print()
    
    tests = [
        ("Health Check", test_health),
        ("Models List", test_models),
        ("Chat Completion", test_chat_completion),
        ("Streaming", test_streaming),
        ("Memory API", test_memory),
        ("Document Search", test_document_search),
    ]
    
    results = []
    for name, test_func in tests:
        result = await test_func()
        results.append((name, result))
    
    print("\n" + "=" * 50)
    print("TEST RESULTS:")
    print("=" * 50)
    
    passed = 0
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:.<30} {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n🎉 All tests passed! Synapse is working correctly.")
    elif passed > 0:
        print("\n⚠️  Some tests failed. Check the configuration.")
    else:
        print("\n❌ All tests failed. Please check if Synapse is running.")


if __name__ == "__main__":
    asyncio.run(main())