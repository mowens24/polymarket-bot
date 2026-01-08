import requests

response = requests.get("https://gamma-api.polymarket.com/tags", params={"limit": 200})
tags = response.json()

print("Relevant tags:")
for t in tags:
    name = t.get("name", "").lower()
    if (
        "crypto" in name
        or "bitcoin" in name
        or "minute" in name
        or "15" in name
        or "up" in name
        or "down" in name
    ):
        print(
            f"ID: {t['id']} | Name: {t.get('name')} | Description: {t.get('description', 'N/A')}"
        )
