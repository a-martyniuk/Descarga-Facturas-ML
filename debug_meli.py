import requests
from meli_invoices import get_headers, BASE_URL

test_ids = ['2000014370308410', '2000014370302836', '2000014547190024']

for tid in test_ids:
    print(f"\n--- Probando ID: {tid} ---")
    # Obtener orden primero para ver pack_id real
    o_url = f"{BASE_URL}/orders/{tid}"
    o_resp = requests.get(o_url, headers=get_headers())
    order_data = o_resp.json()
    p_id = order_data.get('pack_id')
    print(f"Order ID: {tid}, Pack ID found: {p_id}")
    
    target = p_id if p_id else tid
    url = f"{BASE_URL}/packs/{target}/fiscal_documents"
    resp = requests.get(url, headers=get_headers())
    print(f"Fiscal Docs Status: {resp.status_code}")
    print(f"Fiscal Docs Body: {resp.text[:500]}")

