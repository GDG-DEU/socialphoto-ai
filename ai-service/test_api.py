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
        return job_id
    else:
        print("\n❌ Failed to create job")
        return None

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
    else:
        print(f"\n⚠️  Job status: {response.json().get('status')}")

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
    else:
        print("\n❌ Expected 404 status code")

if __name__ == "__main__":
    try:
        print("\n🚀 Starting AI Service API Tests\n")
        
        # Test 1: Create a job
        job_id = test_analyze_endpoint()
        
        if job_id:
            # Test 2: Check job status
            test_job_status(job_id)
        
        # Test 3: Invalid job ID
        test_nonexistent_job()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed!")
        print("=" * 50)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API server at", BASE_URL)
        print("Make sure the server is running with: python main.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
