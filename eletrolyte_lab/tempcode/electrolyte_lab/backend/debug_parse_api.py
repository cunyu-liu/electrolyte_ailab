#!/usr/bin/env python3
"""
直接调试parse-request API端点 - 找出真正的问题
"""

import requests
import json
import traceback
import sys

def debug_parse_request():
    """调试parse-request端点"""

    print("=== DEBUG parse-request API ===")

    url = "http://localhost:5009/api/ai-designer/parse-request"

    # 测试数据
    test_data = {
        "input": "我需要开发一个正极材料，用于动力电池，能量密度要达到280Wh/kg"
    }

    print(f"URL: {url}")
    print(f"Data: {json.dumps(test_data, ensure_ascii=False)}")

    try:
        print("Sending request...")
        response = requests.post(
            url,
            json=test_data,
            timeout=60,
            headers={'Content-Type': 'application/json'}
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Length: {len(response.text)}")

        if response.status_code == 200:
            print("Request SUCCESS!")
            try:
                result = response.json()
                print(f"JSON Parse SUCCESS!")
                print(f"success: {result.get('success')}")
                print(f"message: {result.get('message')}")

                if result.get('data'):
                    data = result.get('data')
                    basic_info = data.get('basic_info', {})
                    print(f"system_type: {basic_info.get('system_type', {}).get('value')}")
                    print(f"application: {basic_info.get('application_scenario', {}).get('value')}")

                    perf_params = data.get('performance_params', {})
                    print(f"energy_density: {perf_params.get('energy_density', {}).get('value')}")

                    print("=== DATA STRUCTURE COMPLETE ===")
                    return True
                else:
                    print("MISSING data field")
                    return False

            except json.JSONDecodeError as e:
                print(f"JSON Parse FAILED: {e}")
                print(f"Raw Response: {response.text[:500]}")
                return False

        else:
            print(f"HTTP ERROR: {response.status_code}")
            try:
                error_json = response.json()
                print(f"Error Details: {error_json}")
            except:
                print(f"Error Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("REQUEST TIMEOUT")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"CONNECTION ERROR: {e}")
        return False
    except Exception as e:
        print(f"UNKNOWN ERROR: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_parse_request()

    if success:
        print("\n=== API TEST SUCCESS ===")
        print("The parse-request API is working correctly!")
        sys.exit(0)
    else:
        print("\n=== API TEST FAILED ===")
        print("There is a problem with the parse-request API")
        sys.exit(1)