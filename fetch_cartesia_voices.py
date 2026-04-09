"""Fetch all available Cartesia TTS voices and save to JSON."""
import requests
import json

API_KEY = "sk_car_7QqSF9RbebzaELHtggdw3E"
URL = "https://api.cartesia.ai/voices"
HEADERS = {
    "X-API-Key": API_KEY,
    "Cartesia-Version": "2024-06-10",
}

print("Fetching voices from Cartesia API...")
resp = requests.get(URL, headers=HEADERS)
resp.raise_for_status()
voices = resp.json()

# Save full response to JSON
with open("cartesia_voices.json", "w", encoding="utf-8") as f:
    json.dump(voices, f, indent=2, ensure_ascii=False)

# Print all voice names and IDs
if isinstance(voices, list):
    voice_list = voices
elif isinstance(voices, dict) and "voices" in voices:
    voice_list = voices["voices"]
else:
    voice_list = voices if isinstance(voices, list) else [voices]

print(f"\nTotal voices: {len(voice_list)}\n")
print(f"{'Voice Name':<40} {'ID'}")
print("-" * 80)
for v in sorted(voice_list, key=lambda x: x.get("name", "")):
    name = v.get("name", "?")
    vid = v.get("id", "?")
    lang = v.get("language", "")
    print(f"{name:<40} {vid}  {lang}")

print(f"\nSaved full data to cartesia_voices.json")
