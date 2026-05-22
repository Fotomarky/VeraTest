"""Generate sample landing-page variants for testing SimAB end-to-end.

Run this once to create:
  tests/fixtures/variant_a.png  — minimal headline, single CTA
  tests/fixtures/variant_b.png  — busier layout with pricing table

These give you real images to upload to the dashboard so you can verify the
whole pipeline without needing to find or screenshot real pages.

Usage:
  python tests/fixtures/make_samples.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Try a few common fonts, fall back to default."""
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/segoeui.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def make_variant_a(out_path: Path) -> None:
    """Minimal landing page: bold headline, one CTA, white space."""
    W, H = 1200, 800
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    # Logo
    d.rectangle([60, 40, 200, 80], fill="#111827")
    d.text((75, 48), "FlowKit", fill="white", font=_load_font(20))

    # Nav (sparse)
    for i, label in enumerate(["Pricing", "Docs", "Log in"]):
        d.text((900 + i * 100, 52), label, fill="#374151", font=_load_font(15))

    # Hero headline
    d.text((W // 2, 230), "Ship faster. Sleep better.",
           fill="#111827", font=_load_font(56), anchor="mm")

    # Sub-headline
    d.text((W // 2, 310),
           "The CI tool that finds bugs before production. Free for small teams.",
           fill="#6b7280", font=_load_font(22), anchor="mm")

    # CTA button (single, centered)
    btn_w, btn_h = 240, 64
    btn_x = (W - btn_w) // 2
    btn_y = 400
    d.rounded_rectangle([btn_x, btn_y, btn_x + btn_w, btn_y + btn_h],
                        radius=8, fill="#2563eb")
    d.text((W // 2, btn_y + btn_h // 2), "Start free trial",
           fill="white", font=_load_font(20), anchor="mm")

    # Trust line
    d.text((W // 2, 510), "No credit card · 14-day trial · Cancel anytime",
           fill="#9ca3af", font=_load_font(14), anchor="mm")

    img.save(out_path, "PNG")


def make_variant_b(out_path: Path) -> None:
    """Busier landing page: pricing table, multiple CTAs, social proof."""
    W, H = 1200, 800
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    # Header
    d.rectangle([0, 0, W, 70], fill="#111827")
    d.text((60, 24), "FlowKit", fill="white", font=_load_font(22))
    for i, label in enumerate(["Features", "Pricing", "Customers", "Docs", "Log in"]):
        d.text((720 + i * 90, 28), label, fill="#d1d5db", font=_load_font(14))
    # Header CTA
    d.rounded_rectangle([W - 180, 18, W - 60, 52], radius=4, fill="#2563eb")
    d.text((W - 120, 35), "Get started", fill="white",
           font=_load_font(13), anchor="mm")

    # Hero (smaller, with stats)
    d.text((60, 130), "Catch 94% of bugs",
           fill="#111827", font=_load_font(42))
    d.text((60, 180), "before they hit production",
           fill="#111827", font=_load_font(42))
    d.text((60, 250),
           "Used by 12,000+ engineering teams. Detect regressions in 30 seconds.",
           fill="#6b7280", font=_load_font(16))

    # Two CTAs side-by-side
    d.rounded_rectangle([60, 300, 220, 350], radius=6, fill="#2563eb")
    d.text((140, 325), "Start free trial", fill="white",
           font=_load_font(15), anchor="mm")
    d.rounded_rectangle([240, 300, 400, 350], radius=6, outline="#2563eb", width=2)
    d.text((320, 325), "Book a demo", fill="#2563eb",
           font=_load_font(15), anchor="mm")

    # Pricing table preview (3 columns)
    table_top = 420
    col_w = 320
    for i, (name, price, features) in enumerate([
        ("Starter", "$0", ["5 projects", "Community support"]),
        ("Pro", "$29/mo", ["Unlimited projects", "Priority support", "SSO"]),
        ("Team", "$99/mo", ["10 seats", "Audit logs", "SLA"]),
    ]):
        x = 60 + i * (col_w + 20)
        highlight = i == 1  # Highlight middle tier
        bg = "#eff6ff" if highlight else "#f9fafb"
        border = "#2563eb" if highlight else "#e5e7eb"
        d.rounded_rectangle([x, table_top, x + col_w, table_top + 280],
                            radius=8, fill=bg, outline=border, width=2)
        d.text((x + 20, table_top + 20), name,
               fill="#111827", font=_load_font(20))
        d.text((x + 20, table_top + 60), price,
               fill="#111827", font=_load_font(30))
        for j, feat in enumerate(features):
            d.text((x + 20, table_top + 130 + j * 28),
                   f"✓ {feat}", fill="#374151", font=_load_font(14))
        # Per-tier CTA
        d.rounded_rectangle([x + 20, table_top + 230, x + col_w - 20, table_top + 265],
                            radius=4,
                            fill="#2563eb" if highlight else "#e5e7eb")
        d.text((x + col_w // 2, table_top + 247),
               "Choose plan", fill="white" if highlight else "#374151",
               font=_load_font(13), anchor="mm")

    img.save(out_path, "PNG")


def main() -> None:
    out_dir = Path(__file__).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    a_path = out_dir / "variant_a.png"
    b_path = out_dir / "variant_b.png"
    make_variant_a(a_path)
    make_variant_b(b_path)
    print(f"✓ Wrote {a_path}")
    print(f"✓ Wrote {b_path}")
    print()
    print("Upload these two images to http://localhost:3000/new to test SimAB.")
    print("Suggested goal: 'sign up for free trial'")
    print("Suggested audience: 'startup founders evaluating CI tools'")


if __name__ == "__main__":
    main()
