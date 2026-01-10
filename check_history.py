import requests
from meli_invoices import get_headers, BASE_URL

user_id = '51746963'
url = f"{BASE_URL}/orders/search?buyer={user_id}&limit=1&offset=0"
resp = requests.get(url, headers=get_headers())
data = resp.json()
total = data.get('paging', {}).get('total', 0)
print(f"Total de órdenes encontradas: {total}")

# Recientes (desc)
url_new = f"{BASE_URL}/orders/search?buyer={user_id}&limit=5&sort=date_desc"
resp_new = requests.get(url_new, headers=get_headers())
newest = resp_new.json().get('results', [])
print("\n--- 5 Órdenes más Recientes ---")
for o in newest:
    print(f"ID: {o.get('id')} - Fecha: {o.get('date_created')}")

# Antiguas (asc)
url_old = f"{BASE_URL}/orders/search?buyer={user_id}&limit=5&sort=date_asc"
resp_old = requests.get(url_old, headers=get_headers())
oldest = resp_old.json().get('results', [])
print("\n--- 5 Órdenes más Antiguas ---")
for o in oldest:
    print(f"ID: {o.get('id')} - Fecha: {o.get('date_created')}")

