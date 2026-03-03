import google.generativeai as genai

# Test the API key and model
genai.configure(api_key='AIzaSyDK2HloHH2B9JzID0E7w1Jq3Sds9x7YpzA')

print("Testing Gemini API...")
print("\nAvailable models:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"  - {m.name}")

print("\nTesting gemini-1.5-pro...")
try:
    model = genai.GenerativeModel('gemini-1.5-pro')
    response = model.generate_content("Say 'Hello, I am working!'")
    print(f"✅ SUCCESS: {response.text}")
except Exception as e:
    print(f"❌ ERROR: {e}")
