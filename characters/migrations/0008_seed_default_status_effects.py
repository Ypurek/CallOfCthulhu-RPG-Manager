from django.db import migrations


DEFAULT_STATUS_EFFECTS = [
    {
        "name": "Deep Wound",
        "description": "A serious injury that prevents normal natural healing until treated.",
        "effect_type": "DEEP_WOUND",
        "is_permanent": False,
        "icon_class": "bi-heart-pulse-fill",
        "game_rules_json": {
            "natural_healing_blocked": True,
            "weekly_con_roll": True,
        },
    },
    {
        "name": "Near Death",
        "description": "The character is at 0 HP and must keep fighting for survival.",
        "effect_type": "NORMAL",
        "is_permanent": False,
        "icon_class": "bi-emoji-dizzy-fill",
        "game_rules_json": {
            "con_roll_each_turn": True,
        },
    },
    {
        "name": "Psychological Trauma",
        "description": "The character suffered severe SAN loss and risks an episode of madness.",
        "effect_type": "MADNESS",
        "is_permanent": False,
        "icon_class": "bi-brain",
        "game_rules_json": {
            "int_roll_required": True,
        },
    },
    {
        "name": "Stunned",
        "description": "The character is stunned and acts with severe limitations.",
        "effect_type": "NORMAL",
        "is_permanent": False,
        "icon_class": "bi-stars",
        "game_rules_json": {},
    },
    {
        "name": "Restrained",
        "description": "The character is physically restrained or immobilized.",
        "effect_type": "NORMAL",
        "is_permanent": False,
        "icon_class": "bi-universal-access-circle",
        "game_rules_json": {},
    },
    {
        "name": "Poisoned",
        "description": "The character is suffering from poison or venom.",
        "effect_type": "NORMAL",
        "is_permanent": False,
        "icon_class": "bi-capsule-pill",
        "game_rules_json": {},
    },
    {
        "name": "Arachnophobia",
        "description": "An intense fear of spiders.",
        "effect_type": "PHOBIA",
        "is_permanent": True,
        "icon_class": "bi-bug-fill",
        "game_rules_json": {},
    },
    {
        "name": "Acrophobia",
        "description": "An intense fear of heights.",
        "effect_type": "PHOBIA",
        "is_permanent": True,
        "icon_class": "bi-building-fill-exclamation",
        "game_rules_json": {},
    },
    {
        "name": "Claustrophobia",
        "description": "An intense fear of confined spaces.",
        "effect_type": "PHOBIA",
        "is_permanent": True,
        "icon_class": "bi-door-closed-fill",
        "game_rules_json": {},
    },
    {
        "name": "Thanatophobia",
        "description": "An intense fear of death or dying.",
        "effect_type": "PHOBIA",
        "is_permanent": True,
        "icon_class": "bi-moon-stars-fill",
        "game_rules_json": {},
    },
    {
        "name": "Dementia",
        "description": "A lingering state of cognitive breakdown and confusion.",
        "effect_type": "MADNESS",
        "is_permanent": False,
        "icon_class": "bi-brain",
        "game_rules_json": {},
    },
    {
        "name": "Paranoia",
        "description": "The character becomes suspicious, fearful, and distrustful.",
        "effect_type": "MADNESS",
        "is_permanent": False,
        "icon_class": "bi-eye-fill",
        "game_rules_json": {},
    },
    {
        "name": "Phobia",
        "description": "A generalized or undefined phobic response.",
        "effect_type": "MADNESS",
        "is_permanent": False,
        "icon_class": "bi-exclamation-triangle-fill",
        "game_rules_json": {},
    },
    {
        "name": "Kleptomania",
        "description": "An uncontrollable urge to steal.",
        "effect_type": "MANIA",
        "is_permanent": False,
        "icon_class": "bi-handbag-fill",
        "game_rules_json": {},
    },
    {
        "name": "Pyromania",
        "description": "An obsessive urge related to fire.",
        "effect_type": "MANIA",
        "is_permanent": False,
        "icon_class": "bi-fire",
        "game_rules_json": {},
    },
    {
        "name": "Compulsive Behavior",
        "description": "A recurring compulsive behavior that is difficult to resist.",
        "effect_type": "MANIA",
        "is_permanent": False,
        "icon_class": "bi-arrow-repeat",
        "game_rules_json": {},
    },
]


def seed_status_effects(apps, schema_editor):
    StatusEffect = apps.get_model("characters", "StatusEffect")
    for effect in DEFAULT_STATUS_EFFECTS:
        StatusEffect.objects.get_or_create(
            name=effect["name"],
            defaults=effect,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("characters", "0007_seed_status_effects"),
    ]

    operations = [
        migrations.RunPython(seed_status_effects, migrations.RunPython.noop),
    ]
