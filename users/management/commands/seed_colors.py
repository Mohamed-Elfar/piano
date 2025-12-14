from django.core.management.base import BaseCommand
from django.db import transaction
from pathlib import Path
import json

from users.models import Color, Product

# Canonical palette we want available in the backend. These are chosen
# to cover the colors shown in the screenshot and common UI palette.
CANONICAL_PALETTE = [
    {"name": "Black", "hex_code": "#000000"},
    {"name": "White", "hex_code": "#F4F3EF"},  # matches sample slightly warm white
    {"name": "Red", "hex_code": "#AF2A4D"},
    {"name": "Orange", "hex_code": "#C46D00"},
    {"name": "Warm Yellow", "hex_code": "#FFDD00"},
    {"name": "Green", "hex_code": "#3D8E4E"},
    {"name": "Mint Gray", "hex_code": "#7A9274"},
    {"name": "Brown", "hex_code": "#D4BCA4"},
    {"name": "Dark Brown", "hex_code": "#885A38"},
    {"name": "Dark Blue", "hex_code": "#3D6F8E"},
    # Optional extended palette (visible in frontend)
    {"name": "Blue", "hex_code": "#007AFF"},
    {"name": "Purple", "hex_code": "#AF52DE"},
    {"name": "Teal", "hex_code": "#5AC8FA"},
    {"name": "Pink", "hex_code": "#FF2D55"},
    {"name": "Navy", "hex_code": "#1F3A5F"},
    {"name": "Olive", "hex_code": "#556B2F"},
    {"name": "Lavender", "hex_code": "#E6E6FA"},
    {"name": "Gray", "hex_code": "#8E8E93"},
]

class Command(BaseCommand):
    help = "Seed and normalize colors in the database; optionally attach to products based on products_sample.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--attach-to-products",
            action="store_true",
            help="Attach colors to Product.colors based on products_sample.json if available",
        )
        parser.add_argument(
            "--sample-path",
            default=str(Path(__file__).resolve().parents[3] / "products_sample.json"),
            help="Path to products_sample.json (defaults to project root)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        updated = 0

        # 1) Ensure canonical palette exists (create or update by hex_code)
        for c in CANONICAL_PALETTE:
            hex_code = c["hex_code"].upper()
            name = c["name"]

            by_hex = Color.objects.filter(hex_code=hex_code).first()
            by_name = Color.objects.filter(name__iexact=name).first()

            # If both exist and are different, merge them
            if by_hex and by_name and by_hex.id != by_name.id:
                # Move product relations from by_name -> by_hex
                for prod in by_name.products.all():
                    prod.colors.add(by_hex)
                # Move product_images relations
                for img in by_name.product_images.all():
                    img.color = by_hex
                    img.save(update_fields=["color"]) 
                # Update canonical fields on by_hex
                if by_hex.name != name:
                    by_hex.name = name
                    by_hex.save(update_fields=["name"]) 
                    updated += 1
                # Delete the duplicate
                by_name.delete()
                obj = by_hex
            else:
                obj = by_hex or by_name
                if obj:
                    changed = False
                    if obj.name != name:
                        obj.name = name
                        changed = True
                    if obj.hex_code.upper() != hex_code:
                        obj.hex_code = hex_code
                        changed = True
                    if changed:
                        obj.save(update_fields=["name", "hex_code"]) 
                        updated += 1
                else:
                    obj = Color.objects.create(name=name, hex_code=hex_code)
                    created += 1

        self.stdout.write(self.style.SUCCESS(f"Colors seeded: created={created}, updated={updated}"))

        # 2) Optionally attach colors to products using products_sample.json
        if options.get("attach_to_products"):
            sample_path = Path(options.get("sample_path"))
            if not sample_path.exists():
                self.stdout.write(self.style.WARNING(f"Sample file not found: {sample_path}"))
                return
            try:
                # Use utf-8-sig to handle BOM if present
                with open(sample_path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to read sample file: {e}"))
                return

            # Map products by id or name to ensure robustness
            attached_pairs = 0
            for item in data:
                # Find product by id first, fallback to name
                product = None
                pid = item.get("id")
                pname = item.get("name")
                if pid is not None:
                    product = Product.objects.filter(id=pid).first()
                if product is None and pname:
                    product = Product.objects.filter(name__iexact=pname).first()
                if product is None:
                    continue

                colors_list = item.get("colors") or []
                for c in colors_list:
                    hex_code = (c.get("hex_code") or "").upper()
                    name = c.get("name") or hex_code
                    if not hex_code:
                        continue
                    color_obj, _ = Color.objects.get_or_create(hex_code=hex_code, defaults={"name": name})
                    # Add to product if missing
                    if not product.colors.filter(id=color_obj.id).exists():
                        product.colors.add(color_obj)
                        attached_pairs += 1
            self.stdout.write(self.style.SUCCESS(f"Product color attachments added: {attached_pairs}"))

        # 3) Summary
        total_colors = Color.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Total colors in DB: {total_colors}"))