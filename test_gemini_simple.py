import google.generativeai as genai

genai.configure(api_key="AIzaSyDK2HloHH2B9JzID0E7w1Jq3Sds9x7YpzA")

model = genai.GenerativeModel("gemini-1.5-flash")

response = model.generate_content("Say hello")

print(response.text)
