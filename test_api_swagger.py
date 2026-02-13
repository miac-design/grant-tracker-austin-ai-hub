#!/usr/bin/env python3
"""
Test script to verify the API is working for Swagger UI.
"""

import requests
import json

def test_opportunities_endpoint():
    """Test the /opportunities endpoint."""
    print("🧪 Testing /opportunities endpoint...")
    
    # Test with defaults
    url = "http://127.0.0.1:8000/opportunities"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Found {data['count']} opportunities")
        print(f"   Total fetched: {data['total_fetched']}")
        print(f"   Last updated: {data['last_updated']}")
        
        if data['results']:
            first_opp = data['results'][0]
            print(f"\n📋 First opportunity:")
            print(f"   Title: {first_opp['title']}")
            print(f"   Agency: {first_opp['agency']}")
            print(f"   Score: {first_opp['total_score']}")
            print(f"   Why it fits: {first_opp['why_it_fits']}")
            print(f"   Deadline: {first_opp['deadline']}")
            print(f"   Award: {first_opp['award']}")
        else:
            print("❌ No opportunities returned")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
    
    # Test with specific parameters
    print(f"\n🔍 Testing with parameters...")
    url = "http://127.0.0.1:8000/opportunities?days=180&min_score=40&only_open=true"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Found {data['count']} opportunities with filters")
        print(f"   Filters: {data['filters']}")
    else:
        print(f"❌ Error: {response.status_code}")

def test_swagger_ui():
    """Test if Swagger UI is accessible."""
    print(f"\n🌐 Testing Swagger UI...")
    
    try:
        response = requests.get("http://127.0.0.1:8000/docs")
        if response.status_code == 200:
            print("✅ Swagger UI is accessible at http://127.0.0.1:8000/docs")
        else:
            print(f"❌ Swagger UI error: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot access Swagger UI: {e}")

if __name__ == "__main__":
    print("🚀 Testing Dental AI Grant Finder API for Swagger UI...")
    test_opportunities_endpoint()
    test_swagger_ui()
    print("\n🎉 Test completed!")
    print("\n📖 To test in Swagger UI:")
    print("   1. Go to http://127.0.0.1:8000/docs")
    print("   2. Expand /opportunities")
    print("   3. Click 'Try it out'")
    print("   4. Use defaults or set parameters")
    print("   5. Click 'Execute'")
    print("   6. You should see at least 1 open grant!") 