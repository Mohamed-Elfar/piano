from django.core.management.base import BaseCommand

from users.models import Governorate, Area


EGYPT_GOVS = [
    {
        "name": "Cairo",
        "areas": ["Nasr City", "Maadi", "Heliopolis", "Zamalek", "Shubra"]
    },
    {
        "name": "Giza",
        "areas": ["Dokki", "Mohandessin", "Haram", "6th of October", "Sheikh Zayed"]
    },
    {
        "name": "Alex",
        "areas": ["Sidi Gaber", "Stanley", "Roushdy", "Miami", "Alex"]
    },
    {
        "name": "Aswan",
        "areas": ["Aswan City", "Kom Ombo", "Edfu"]
    },
    {
        "name": "Luxor",
        "areas": ["Luxor City", "Al Qurna", "Esna"]
    },
    {
        "name": "Qalyubia",
        "areas": ["Shubra El Kheima", "Banha", "Tukh"]
    },
    {
        "name": "Beheira",
        "areas": ["Damanhour", "Kafr El Dawar"]
    },
]


class Command(BaseCommand):
    help = "Populate database with common Egyptian governorates and areas (idempotent)."

    def handle(self, *args, **options):
        created_govs = 0
        created_areas = 0

        for gov in EGYPT_GOVS:
            gov_obj, gov_created = Governorate.objects.get_or_create(name=gov["name"]) 
            if gov_created:
                created_govs += 1
                self.stdout.write(self.style.SUCCESS(f"Created governorate: {gov_obj.name}"))
            else:
                self.stdout.write(f"Governorate exists: {gov_obj.name}")

            for area_name in gov.get("areas", []):
                area_obj, area_created = Area.objects.get_or_create(
                    name=area_name,
                    governorate=gov_obj,
                    defaults={"shipping_cost": 0.00},
                )
                if area_created:
                    created_areas += 1
                    self.stdout.write(self.style.SUCCESS(f"  Created area: {area_obj.name} ({gov_obj.name})"))
                else:
                    self.stdout.write(f"  Area exists: {area_obj.name} ({gov_obj.name})")

        self.stdout.write(self.style.SUCCESS(f"Done. Governorates created: {created_govs}, Areas created: {created_areas}"))
