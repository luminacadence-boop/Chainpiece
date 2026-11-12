import io, re
from app import create_app

app = create_app({"SECRET_KEY": "smoke-test-key"})
client = app.test_client()

r = client.get("/")
print("home page:", r.status_code)

r = client.post("/signup", data={
    "email": "founder@example.com", "display_name": "Founder",
    "password": "smithsonian-vault-1"})
print("account created:", r.status_code)

png = b"\x89PNG\r\n\x1a\n" + b"fake-image-data" * 10
r = client.post("/objects/new", data={
    "category": "coin", "title": "1893-S Morgan Silver Dollar",
    "description": "Key-date Morgan dollar, circulated",
    "attr_date": "1893", "attr_mint_mark": "S",
    "attr_weight": "26.73 grams",
    "attr_features": "VAM-4; hairpin scratch above S mint mark",
    "photos": [(io.BytesIO(png), "obverse.png"), (io.BytesIO(png), "reverse.png")],
}, content_type="multipart/form-data", follow_redirects=True)
print("object registered:", r.status_code)
body = r.get_data(as_text=True)
reg_id = re.search(r"CRN-[A-Z2-9]{5}-[A-Z2-9]{5}", body).group(0)
print("permanent registration ID:", reg_id)
print("photo shown on page:", "<img" in body)
print("chain badge:", "Custody chain intact" in body)

r = client.post(f"/objects/{reg_id}/events", data={
    "event_type": "ownership_claim",
    "details": "Purchased from Heritage Auction, January 2031, lot 4211"},
    follow_redirects=True)
print("custody event recorded:", "Purchased from Heritage Auction" in r.get_data(as_text=True))

page = client.get(f"/objects/{reg_id}").get_data(as_text=True)
print("history entries:", page.count("<li>"))
print("public profile reachable:", client.get(f"/objects/{reg_id}").status_code)
