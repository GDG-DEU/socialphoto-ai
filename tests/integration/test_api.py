#!/usr/bin/env python3
"""Test script for AI Service API"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_analyze_endpoint():
    """Test POST /analyze endpoint"""
    print("=" * 50)
    print("TEST 1: POST /analyze")
    print("=" * 50)
    
    payload = {
        "post_id": "test_post_123",
        "image_url": "https://example.com/test-image.jpg"
    }
    
    response = requests.post(f"{BASE_URL}/analyze", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 202:
        job_id = response.json()["job_id"]
        print(f"\n✅ Job created successfully! Job ID: {job_id}")
        return job_id, True
    else:
        print("\n❌ Failed to create job")
        return None, False

def test_job_status(job_id):
    """Test GET /analyze/{job_id} endpoint"""
    print("\n" + "=" * 50)
    print(f"TEST 2: GET /analyze/{job_id}")
    print("=" * 50)
    
    # Check status immediately
    response = requests.get(f"{BASE_URL}/analyze/{job_id}")
    print(f"Status Code: {response.status_code}")
    print(f"Initial Status: {json.dumps(response.json(), indent=2)}")
    
    # Wait for worker to process (3 seconds + buffer)
    print("\n⏳ Waiting for worker to process job (4 seconds)...")
    time.sleep(4)
    
    # Check status again
    response = requests.get(f"{BASE_URL}/analyze/{job_id}")
    print(f"\nFinal Status: {json.dumps(response.json(), indent=2)}")
    
    if response.json().get("status") == "completed":
        print("\n✅ Job completed successfully!")
        print(f"Results: {response.json().get('result')}")
        return True
    else:
        print(f"\n⚠️  Job status: {response.json().get('status')}")
        return False

def test_nonexistent_job():
    """Test GET /analyze/{job_id} with invalid ID"""
    print("\n" + "=" * 50)
    print("TEST 3: GET /analyze/invalid-job-id")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/analyze/fake-job-123")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 404:
        print("\n✅ Correctly returned 404 for non-existent job")
        return True
    else:
        print("\n❌ Expected 404 status code")
        return False

def test_similarity_search():
    """Test POST /sim-search endpoint"""
    print("\n" + "=" * 50)
    print("TEST 4: POST /sim-search")
    print("=" * 50)
    
    passed = 0
    total = 4
    
    # Test with text query
    payload = {
        "query_text": "beautiful sunset",
        "top_k": 3
    }
    
    response = requests.post(f"{BASE_URL}/sim-search", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response (text query): {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        results = response.json().get("results", [])
        print(f"\n✅ Similarity search successful! Found {len(results)} results")
        passed += 1
    else:
        print("\n❌ Similarity search failed")
    
    # Test with image URL
    print("\n" + "-" * 50)
    payload = {
        "image_url": "https://example.com/query-image.jpg",
        "top_k": 2
    }
    
    response = requests.post(f"{BASE_URL}/sim-search", json=payload)
    print(f"Response (image query): {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        results = response.json().get("results", [])
        print(f"✅ Found {len(results)} similar images")
        passed += 1
    else:
        print("❌ Image similarity search failed")
    
    # Test with both text and image
    print("\n" + "-" * 50)
    payload = {
        "query_text": "mountain landscape",
        "image_url": "https://example.com/mountain.jpg",
        "top_k": 5
    }
    
    response = requests.post(f"{BASE_URL}/sim-search", json=payload)
    print(f"Response (combined query): {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✅ Combined query successful")
        passed += 1
    else:
        print("❌ Combined query failed")
    
    # Test with neither text nor image (should fail with 400)
    print("\n" + "-" * 50)
    payload = {
        "top_k": 3
    }
    
    response = requests.post(f"{BASE_URL}/sim-search", json=payload)
    print(f"Response (no query): {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 400:
        print("✅ Correctly rejected empty query with 400")
        passed += 1
    else:
        print(f"❌ Expected 400 status code, got {response.status_code}")
    
    return passed == total

def test_chat_endpoint():
    """Test POST /chat endpoint"""
    print("\n" + "=" * 50)
    print("TEST 5: POST /chat")
    print("=" * 50)
    
    passed = 0
    total = 4
    
    # Test basic chat
    payload = {
        "user_id": "user_123",
        "message": "Hello, how are you?"
    }
    
    response = requests.post(f"{BASE_URL}/chat", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response (basic chat): {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200 and response.json().get("reply"):
        print("\n✅ Basic chat successful!")
        passed += 1
    else:
        print("\n❌ Basic chat failed")
    
    # Test chat with "search" keyword (should trigger action)
    print("\n" + "-" * 50)
    payload = {
        "user_id": "user_123",
        "message": "Can you search for sunset images?"
    }
    
    response = requests.post(f"{BASE_URL}/chat", json=payload)
    print(f"Response (search keyword): {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        actions = response.json().get("actions", [])
        if actions and any(a.get("type") == "search_images" for a in actions):
            print("✅ Search action triggered correctly")
            passed += 1
        else:
            print("⚠️  Expected search_images action")
    else:
        print("❌ Search keyword chat failed")
    
    # Test chat with "analyze" keyword (should trigger action)
    print("\n" + "-" * 50)
    payload = {
        "user_id": "user_456",
        "message": "Please analyze this photo for me"
    }
    
    response = requests.post(f"{BASE_URL}/chat", json=payload)
    print(f"Response (analyze keyword): {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        actions = response.json().get("actions", [])
        if actions and any(a.get("type") == "analyze_photo" for a in actions):
            print("✅ Analyze action triggered correctly")
            passed += 1
        else:
            print("⚠️  Expected analyze_photo action")
    else:
        print("❌ Analyze keyword chat failed")
    
    # Test chat with history
    print("\n" + "-" * 50)
    payload = {
        "user_id": "user_789",
        "message": "What did I ask before?",
        "history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
    }
    
    response = requests.post(f"{BASE_URL}/chat", json=payload)
    print(f"Response (with history): {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✅ Chat with history successful")
        passed += 1
    else:
        print("❌ Chat with history failed")
    
    return passed == total

def test_health_endpoint():
    """Test GET /health endpoint"""
    print("\n" + "=" * 50)
    print("TEST 6: GET /health")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        data = response.json()
        status = data.get("status")
        models_loaded = data.get("models_loaded", [])
        
        if status in ["online", "degraded", "offline"]:
            print(f"\n✅ Health check successful!")
            print(f"   Status: {status}")
            print(f"   Healthy components: {models_loaded}")
            
            # Check if Redis is healthy (should be if server is running)
            if "redis" in models_loaded:
                print("✅ Redis health check passed")
            else:
                print("⚠️  Redis not in healthy components")
            
            return True
        else:
            print(f"\n❌ Unexpected status value: {status}")
            return False
    else:
        print("\n❌ Health check failed")
        return False

if __name__ == "__main__":
    try:
        print("\n🚀 Starting AI Service API Tests\n")
        
        tests_passed = 0
        tests_total = 6
        
        # Test 1: Create a job
        job_id, passed = test_analyze_endpoint()
        if passed:
            tests_passed += 1
        
        if job_id:
            # Test 2: Check job status
            if test_job_status(job_id):
                tests_passed += 1
        
        # Test 3: Invalid job ID
        if test_nonexistent_job():
            tests_passed += 1
        
        # Test 4: Similarity search
        if test_similarity_search():
            tests_passed += 1
        
        # Test 5: Chat endpoint
        if test_chat_endpoint():
            tests_passed += 1
        
        # Test 6: Health endpoint
        if test_health_endpoint():
            tests_passed += 1
        
        print("\n" + "=" * 50)
        print(f"✅ {tests_passed}/{tests_total} tests passed correctly!")
        print("=" * 50)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API server at", BASE_URL)
        print("Make sure the server is running with: python main.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
