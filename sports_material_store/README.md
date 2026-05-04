# contributors
K Harichandra Prasad (CDS/2025/1292)
M Kapil Sravan Kumar (CDS/2025/1236)
E Sai Prashanth (CDS/2025/1240)


# SportStack Sports Marketplace

A local Python Flask ecommerce website inspired by large marketplace layouts. This version is restricted to **sports materials only**. It is not branded as Amazon or Flipkart, but it includes similar marketplace flows: product grid, search, filters, cart, checkout, dealer registration, dealer login, stock management, and an AI shopping assistant.

## Major Features

- Sports-only product dump with 60+ seeded products
- Product card format: picture, category, name, dealer, rating, price, stock, cart
- Internet-based product pictures mapped by product keywords
- Local SVG fallback image if internet is not available
- 3D-style animated product cards and product detail page
- Product detail page for every item
- Cart add/update/remove with stock validation
- Local demo checkout with order receipt
- Dealer registration and login
- Dealer dashboard to add sports products, update stock/price, and delete own products
- Admin dashboard to update product price/stock, view dealers, and view latest orders
- OpenRouter chatbot with local fallback mode when API key is not configured
- SQLite local database
- CSRF protection, security headers, and rate limiting

## Important Scope Rule

This website handles only sports material categories:

- Cricket
- Football
- Badminton
- Basketball
- Tennis
- Gym
- Running
- Swimming
- Cycling
- Boxing
- Fitness
- Accessories

Dealer product creation blocks non-sports categories.

## Run Locally

```bash
cd sports_material_store_upgraded
python -m venv .venv
```

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python app.py
```

### macOS / Linux

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Admin Login

```text
http://127.0.0.1:5000/admin/login
```

Default password:

```text
admin123
```

Change it in `.env`:

```env
ADMIN_PASSWORD=your_strong_password
```

## Dealer Flow

Register dealer:

```text
http://127.0.0.1:5000/dealer/register
```

Dealer login:

```text
http://127.0.0.1:5000/dealer/login
```

After login, the dealer can add products. If the dealer enters image keywords like `cricket bat leather grip`, the app creates an internet image URL for that product. The dealer can also paste a direct `https://...` image URL.

## OpenRouter Chatbot

The chatbot works in two modes:

1. Local fallback mode without API key
2. OpenRouter AI mode with API key

To enable OpenRouter, edit `.env`:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
```

Restart:

```bash
python app.py
```

## Database Reset

The local SQLite database is created automatically inside `instance/sports_store.sqlite3`.

To reset all data:

```bash
rm instance/sports_store.sqlite3
python app.py
```

On Windows PowerShell:

```powershell
Remove-Item .\instance\sports_store.sqlite3
python app.py
```

## Project Structure

```text
sports_material_store_upgraded/
  app.py
  requirements.txt
  .env.example
  README.md
  templates/
  static/
    css/styles.css
    js/app.js
    js/chatbot.js
    images/sports-fallback.svg
  instance/
```

## Notes

- This is a local demo project, not a production payment website.
- Product images are loaded from internet image URLs and include fallback handling.
- For production, add real payment gateway, email/SMS verification, dealer KYC approval, product image upload storage, audit logs, and deployment hardening.

## Strict Product Image Matching Update

This version avoids random image mismatches by using verified generated SVG images as the primary visible catalog pictures. Each seeded product image is stored at:

```text
static/images/products/<product-slug>.svg
```

Each SVG contains:

- The exact product name
- The exact sports category
- A sports-item illustration based on the product type

Dealer-entered internet image URLs are still accepted as backup metadata, but the app prioritizes the verified local product image so the storefront does not show a football picture for a cricket product, or a wrong item for any product name.

## 3D Product View

Open any product page and use:

- Mouse movement for tilt
- ⟲ / ⟳ buttons for manual rotation
- Auto 3D button for continuous spin

## Validation

See `VALIDATION_REPORT.md` for the tested routes and image checks.


## Advanced image/gallery upgrades

This version adds a full product-image workflow:

- Primary image upload for dealer products.
- Primary image upload/replacement from admin dashboard.
- Live image preview before saving.
- Drag-and-drop image upload zones.
- Automatic square crop/resize preview before save.
- Multiple gallery images per product.
- Product detail gallery thumbnails.
- Product detail zoom view.
- 360° product viewer using gallery frames.
- Seeded sports products automatically receive verified matching images and generated 360° frames.
- Uploaded/admin/dealer images are preserved on app restart.

The app still enforces sports-material categories only.
