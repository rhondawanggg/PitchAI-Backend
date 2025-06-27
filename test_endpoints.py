#!/usr/bin/env python3
"""
API Testing Script for PitchAI Backend
Usage: python test_endpoints.py
"""

import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/v1"

def test_endpoint(method: str, endpoint: str, data: Dict[Any, Any] = None, expected_status: int = 200) -> bool:
    """Test a single API endpoint"""
    url = f"{BASE_URL}{endpoint}"

    try:
        if method.upper() == "GET":
            response = requests.get(url)
        elif method.upper() == "POST":
            response = requests.post(url, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url)
        else:
            print(f"❌ Unsupported method: {method}")
            return False

        print(f"🔍 {method.upper()} {endpoint}")
        print(f"   Status: {response.status_code}")

        if response.status_code == expected_status:
            try:
                response_data = response.json()
                print(f"   ✅ Success")
                return True
            except json.JSONDecodeError:
                print(f"   ✅ Success (non-JSON response)")
                return True
        else:
            print(f"   ❌ Expected {expected_status}, got {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Error: {response.text}")
            return False

    except requests.RequestException as e:
        print(f"   ❌ Request failed: {e}")
        return False

def run_tests():
    """Run all API endpoint tests"""
    print("🚀 Testing PitchAI API Endpoints")
    print("=" * 50)

    # Track test results
    results = []

    # Test 1: Health Check
    print("\n📊 Health Check")
    results.append(test_endpoint("GET", "/ping"))

    # Test 2: Project Statistics
    print("\n📊 Project Statistics")
    results.append(test_endpoint("GET", "/projects/statistics"))

    # Test 3: List Projects
    print("\n📊 List Projects")
    results.append(test_endpoint("GET", "/projects"))
    results.append(test_endpoint("GET", "/projects?page=1&size=5"))
    results.append(test_endpoint("GET", "/projects?status=completed"))
    results.append(test_endpoint("GET", "/projects?search=AI"))

    # Test 4: Create Project
    print("\n📊 Create Project")
    new_project_data = {
        "enterprise_name": "测试科技有限公司",
        "project_name": "AI测试项目",
        "description": "这是一个用于API测试的项目"
    }
    results.append(test_endpoint("POST", "/projects", new_project_data, 200))

    # For the following tests, we'll use a known project ID from sample data
    project_id = "550e8400-e29b-41d4-a716-446655440001"

    # Test 5: Get Project Details
    print("\n📊 Get Project Details")
    results.append(test_endpoint("GET", f"/projects/{project_id}"))

    # Test 6: Get Project Scores
    print("\n📊 Get Project Scores")
    results.append(test_endpoint("GET", f"/projects/{project_id}/scores"))

    # Test 7: Update Project Scores
    print("\n📊 Update Project Scores")
    score_update_data = {
        "dimensions": [
            {
                "dimension": "团队能力",
                "score": 27,
                "max_score": 30,
                "comments": "团队经验丰富，更新后的评价",
                "sub_dimensions": [
                    {
                        "sub_dimension": "核心团队背景",
                        "score": 9,
                        "max_score": 10,
                        "comments": "核心成员背景优秀"
                    },
                    {
                        "sub_dimension": "团队完整性",
                        "score": 9,
                        "max_score": 10,
                        "comments": "团队结构完整"
                    },
                    {
                        "sub_dimension": "团队执行力",
                        "score": 9,
                        "max_score": 10,
                        "comments": "执行力强"
                    }
                ]
            }
        ]
    }
    results.append(test_endpoint("PUT", f"/projects/{project_id}/scores", score_update_data))

    # Test 8: Get Missing Information
    print("\n📊 Get Missing Information")
    results.append(test_endpoint("GET", f"/projects/{project_id}/missing-information"))

    # Test 9: Get Score Summary
    print("\n📊 Get Score Summary")
    results.append(test_endpoint("GET", f"/projects/{project_id}/scores/summary"))

    # Test 10: Error Handling
    print("\n📊 Error Handling")
    results.append(test_endpoint("GET", "/projects/invalid-uuid", expected_status=400))
    results.append(test_endpoint("GET", "/projects/550e8400-e29b-41d4-a716-446655440999", expected_status=404))

    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary")
    print("=" * 50)

    passed = sum(results)
    total = len(results)

    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")

    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("💥 Some tests failed!")
        return False

if __name__ == "__main__":
    try:
        success = run_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)