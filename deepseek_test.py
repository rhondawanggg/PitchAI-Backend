#!/usr/bin/env python3
"""
DeepSeek API Key Test Script
Usage: python test_deepseek_api.py
"""

import openai
import os
from dotenv import load_dotenv
import sys

def test_api_key():
    """Test DeepSeek API key configuration and connectivity"""

    print("🔧 DeepSeek API Key Test")
    print("=" * 50)

    # Load environment variables
    load_dotenv()

    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    # Check if API key is configured
    if not api_key:
        print("❌ DEEPSEEK_API_KEY not found in environment variables")
        print("💡 Make sure you have a .env file with:")
        print("   DEEPSEEK_API_KEY=sk-your-key-here")
        return False

    # Display configuration (partially masked)
    print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else 'SHORT'}")
    print(f"🌐 Base URL: {base_url}")
    print(f"📏 Key Length: {len(api_key)} characters")

    # Validate key format
    if not api_key.startswith("sk-"):
        print("⚠️  Warning: API key doesn't start with 'sk-'")
        print("💡 DeepSeek keys should start with 'sk-'")

    if len(api_key) < 40:
        print("⚠️  Warning: API key seems too short")
        print("💡 DeepSeek keys are typically 51+ characters long")

    # Test API connection
    print("\n🧪 Testing API Connection...")

    try:
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )

        print("📡 Sending test request...")

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "你是一个有用的助手。请用中文回答。"
                },
                {
                    "role": "user",
                    "content": "请说'API测试成功'"
                }
            ],
            max_tokens=20,
            temperature=0.1
        )

        result = response.choices[0].message.content.strip()
        print(f"✅ API Test Successful!")
        print(f"📝 Response: {result}")
        print(f"💰 Usage: {response.usage}")

        return True

    except Exception as e:
        print(f"❌ API Test Failed: {e}")

        # Provide specific error guidance
        error_str = str(e).lower()

        if "401" in error_str or "authentication" in error_str:
            print("\n🔧 Authentication Error - Possible Solutions:")
            print("   1. Check if your API key is correct")
            print("   2. Regenerate API key at https://platform.deepseek.com/api_keys")
            print("   3. Make sure you have sufficient credits")
            print("   4. Verify account is active")

        elif "429" in error_str or "rate" in error_str:
            print("\n🔧 Rate Limit Error - Possible Solutions:")
            print("   1. Wait a few minutes and try again")
            print("   2. Check your usage quota")
            print("   3. Upgrade your account if needed")

        elif "403" in error_str or "forbidden" in error_str:
            print("\n🔧 Permission Error - Possible Solutions:")
            print("   1. Check if your account has API access enabled")
            print("   2. Verify billing information is up to date")
            print("   3. Contact DeepSeek support")

        elif "network" in error_str or "connection" in error_str:
            print("\n🔧 Network Error - Possible Solutions:")
            print("   1. Check your internet connection")
            print("   2. Try again in a few minutes")
            print("   3. Check if DeepSeek API is down")

        else:
            print("\n🔧 Unknown Error - General Solutions:")
            print("   1. Double-check your API key")
            print("   2. Try regenerating the API key")
            print("   3. Check DeepSeek service status")

        return False

def test_business_plan_evaluation():
    """Test a simple business plan evaluation"""

    print("\n🧪 Testing Business Plan Evaluation...")

    # Load environment variables
    load_dotenv()

    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    if not api_key:
        print("❌ Cannot test evaluation - API key not configured")
        return False

    try:
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )

        # Simple evaluation test
        test_content = """
        企业名称：测试科技有限公司
        项目名称：AI智能客服系统

        团队介绍：
        CEO张三，具有10年互联网行业经验
        CTO李四，AI技术专家，拥有多项专利

        产品技术：
        基于大语言模型的智能客服系统
        已申请3项核心技术专利

        市场分析：
        客服市场规模达500亿人民币
        年增长率30%以上
        """

        prompt = f"""
请分析以下商业计划书中的团队能力维度，总分30分。

评分标准：
- 核心团队背景 (10分)
- 团队完整性 (10分)
- 团队执行力 (10分)

商业计划书内容：
{test_content}

请返回JSON格式：
{{"score": 总分, "max_score": 30, "comments": "评价"}}
"""

        print("📡 Testing evaluation prompt...")

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的项目评审专家。请严格按照JSON格式返回结果。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=500
        )

        result = response.choices[0].message.content.strip()
        print(f"✅ Evaluation Test Successful!")
        print(f"📝 Raw Response: {result}")

        # Try to parse JSON
        try:
            import json
            if result.startswith("```json"):
                result = result.replace("```json", "").replace("```", "").strip()

            parsed = json.loads(result)
            print(f"✅ JSON Parsing Successful!")
            print(f"📊 Score: {parsed.get('score', 'N/A')}/{parsed.get('max_score', 'N/A')}")
            print(f"💬 Comments: {parsed.get('comments', 'N/A')}")

        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing failed: {e}")
            print("💡 The API is working but response format needs adjustment")

        return True

    except Exception as e:
        print(f"❌ Evaluation Test Failed: {e}")
        return False

def main():
    """Run all API tests"""

    success = True

    # Test 1: Basic API connectivity
    if not test_api_key():
        success = False

    # Test 2: Business plan evaluation (only if basic test passed)
    if success:
        if not test_business_plan_evaluation():
            print("⚠️  Basic API works but evaluation needs tuning")

    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary")
    print("=" * 50)

    if success:
        print("✅ DeepSeek API is working correctly!")
        print("💡 Your PitchAI system should now have AI evaluation")
        print("\n🚀 Next steps:")
        print("   1. Restart your backend server")
        print("   2. Upload a business plan")
        print("   3. Check if AI evaluation runs successfully")
    else:
        print("❌ DeepSeek API configuration needs attention")
        print("\n🔧 Action items:")
        print("   1. Fix API key configuration")
        print("   2. Check account status and credits")
        print("   3. Run this test again")
        print("\n💡 Your PitchAI system still works with manual scoring!")

if __name__ == "__main__":
    main()