#!/usr/bin/env python3
"""
Simple script to test OpenAI client initialization
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_openai_client():
    print("🤖 TESTING OPENAI CLIENT INITIALIZATION")
    print("="*50)
    
    # Check if API key exists
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return
    
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        from openai import OpenAI
        print("✅ OpenAI library imported successfully")
        
        # Initialize client with minimal configuration
        client = OpenAI(
            api_key=api_key
        )
        print("✅ OpenAI client initialized successfully")
        
        # Test a simple API call
        print("🧪 Testing API call...")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Say 'Hello, AI is working!'"}
            ],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"✅ API call successful: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_openai_client()
    exit(0 if success else 1) 