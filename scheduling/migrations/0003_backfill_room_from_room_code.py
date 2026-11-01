"""Backfill the normalized ``Room`` table from existing ``Section.room_code``.

Forward: for each section with a non-blank ``room_code``, get-or-create a ``Room``
with that exact (trimmed) code and point ``section.room`` at it. Blank/TBA room
codes are left as ``room = NULL`` (a TBA room must never become a real room).
Existing ``room_code`` values are preserved untouched. No room details are
invented: a migrated room's ``name`` is set to its code, and building/capacity
stay empty.

Reverse: clear every ``section.room`` and delete the rooms this chain created.
``Room`` is introduced in 0002, so deleting all rooms on reverse is safe.
"""

from django.db import migrations


def backfill_rooms(apps, schema_editor):
    Section = apps.get_model("scheduling", "Section")
    Room = apps.get_model("scheduling", "Room")
    for section in Section.objects.all():
        code = (section.room_code or "").strip()
        if not code:
            # Blank / TBA -> leave room NULL; do not fabricate a room.
            continue
        room, _created = Room.objects.get_or_create(
            room_code=code,
            defaults={"name": code, "is_active": True},
        )
        if section.room_id != room.id:
            section.room = room
            section.save(update_fields=["room"])


def unbackfill_rooms(apps, schema_editor):
    Section = apps.get_model("scheduling", "Section")
    Room = apps.get_model("scheduling", "Room")
    Section.objects.update(room=None)
    Room.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0002_room_model"),
    ]

    operations = [
        migrations.RunPython(backfill_rooms, unbackfill_rooms),
    ]
