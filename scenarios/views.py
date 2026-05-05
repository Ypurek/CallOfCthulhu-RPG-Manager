import json as _json
import secrets
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _t
from django.views.decorators.http import require_POST
from django.db.models import Q as _Q

from characters.models import Character, NPCTemplate, StatusEffect, CharacterStatusEffect, CharacterSkill
from characters.views import _build_character_sheet_context
from core.models import User as _User
from .services import apply_daily_hp_restore, apply_hourly_mp_restore, get_character_status_effects_display
from .models import (
    FightEncounter,
    FightParticipant,
    Hint,
    Invitation,
    Message,
    MessageReceipt,
    Scenario,
    ScenarioNPC,
    ScenarioPlayer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _keeper_required(view_fn):
    """Decorator: user must be a Keeper or admin."""
    from functools import wraps

    @wraps(view_fn)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_keeper() or request.user.is_staff):
            messages.error(request, "Only Keepers can perform this action.")
            return redirect("dashboard")
        return view_fn(request, *args, **kwargs)

    return wrapper


def _get_scenario_for_keeper(request, scenario_id):
    if request.user.is_staff:
        return get_object_or_404(Scenario, id=scenario_id)
    return get_object_or_404(Scenario, id=scenario_id, keeper=request.user)


def _npc_from_template(template: NPCTemplate, keeper, display_name: str = "") -> Character:
    """Create NPC from template through the wizard import pipeline (keeps skills/items/weapons)."""
    from characters.views import _create_npc_character_from_draft, _draft_from_import

    payload = template.payload if isinstance(template.payload, dict) else {}
    draft = _draft_from_import(payload)

    # Scenario-level display name can override template default name.
    if display_name:
        draft.setdefault("basic", {})
        draft["basic"]["name"] = display_name

    return _create_npc_character_from_draft(keeper, draft)


def _clone_npc_character(original: Character, new_name: str) -> Character:
    """Deep-copy a Character and give it a new name."""
    clone = Character(
        owner=original.owner,
        character_type=original.character_type,
        name=new_name,
        birthplace=original.birthplace,
        residence=original.residence,
        occupation=original.occupation,
        gender=original.gender,
        age=original.age,
        description=original.description,
        strength=original.strength,
        constitution=original.constitution,
        dexterity=original.dexterity,
        intelligence=original.intelligence,
        power=original.power,
        size=original.size,
        appearance=original.appearance,
        education=original.education,
        hp_current=original.hp_current,
        hp_max=original.hp_max,
        mp_current=original.mp_current,
        mp_max=original.mp_max,
        sanity_current=original.sanity_current,
        sanity_max=original.sanity_max,
        sanity_start=original.sanity_start,
        luck=original.luck,
        movement=original.movement,
        build=original.build,
        damage_bonus=original.damage_bonus,
        cash=original.cash,
    )
    clone.save()
    return clone


def _build_session_sheet(character: Character):
    """Prepare full sheet payload used by the keeper session view."""
    char_skills = list(character.skills.select_related("skill").all())
    skill_values = {cs.skill_id: cs.value for cs in char_skills}
    needs_update_skill_ids = {cs.skill_id for cs in char_skills if cs.needs_update}
    weapons = [
        {"name": cw.weapon.name, "damage": cw.weapon.damage, "is_prepared": cw.is_prepared}
        for cw in character.weapons.select_related("weapon").all()
    ]
    items = [
        {"name": ci.item.name, "quantity": ci.quantity}
        for ci in character.items.select_related("item").all()
    ]
    spells = [
        {"name": cs.spell.name, "mana_cost": cs.spell.mana_cost}
        for cs in character.spells.select_related("spell").all()
    ]
    sheet = _build_character_sheet_context(
        character=character,
        skill_values=skill_values,
        weapons=weapons,
        items=items,
        spells=spells,
        can_add_custom_skill=False,
        needs_update_skill_ids=needs_update_skill_ids,
    )
    sheet["effects"] = get_character_status_effects_display(character)
    return sheet


def _serialize_session_card(character: Character, display_name: str | None = None):
    """Serialize visible session-card state for AJAX refreshes."""
    return {
        "character_id": character.id,
        "display_name": display_name or character.name,
        "is_alive": character.is_alive,
        "resources": {
            "hp": {"current": character.hp_current, "max": character.hp_max},
            "sanity": {"current": character.sanity_current, "max": character.sanity_max},
            "mp": {"current": character.mp_current, "max": character.mp_max},
            "luck": {"current": character.luck, "max": 100},
        },
        "effects": get_character_status_effects_display(character),
    }


def _get_session_card_updates(scenario: Scenario):
    """Return current PC/NPC card state for the keeper manage page."""
    updates = []

    for sp in ScenarioPlayer.objects.filter(scenario=scenario).select_related("character"):
        if sp.character:
            updates.append(_serialize_session_card(sp.character))

    for snpc in ScenarioNPC.objects.filter(scenario=scenario).select_related("npc"):
        if snpc.npc:
            updates.append(_serialize_session_card(snpc.npc, display_name=snpc.get_display_name()))

    return updates


def _get_scenario_player_users(scenario: Scenario):
    """Return active player users participating in the scenario."""
    return list(
        _User.objects.filter(
            player_scenarios__scenario=scenario,
            player_scenarios__is_active=True,
        ).distinct()
    )


def _create_message_receipts(message: Message):
    """Create delivery receipts for the message recipients."""
    recipients = []
    if message.message_type == "PRIVATE" and message.recipient_id:
        recipients = [message.recipient]
    elif message.message_type in {"PUBLIC", "SYSTEM"}:
        recipients = [user for user in _get_scenario_player_users(message.scenario) if user.id != message.sender_id]

    MessageReceipt.objects.bulk_create(
        [MessageReceipt(message=message, user=user) for user in recipients],
        ignore_conflicts=True,
    )


def _serialize_message(message: Message, receipt: MessageReceipt | None = None):
    return {
        "id": message.id,
        "sender": message.sender.username,
        "content": message.content,
        "type": message.message_type,
        "recipient": message.recipient.username if message.recipient else "",
        "sent_at": message.sent_at.isoformat(),
        "is_unread": bool(receipt and receipt.read_at is None),
    }


def _get_unread_message_count(scenario: Scenario, user: _User) -> int:
    return MessageReceipt.objects.filter(
        message__scenario=scenario,
        user=user,
        read_at__isnull=True,
    ).count()


def _get_latest_unread_private_message_id(scenario: Scenario, user: _User) -> int:
    latest_message_id = (
        MessageReceipt.objects.filter(
            message__scenario=scenario,
            message__message_type="PRIVATE",
            user=user,
            read_at__isnull=True,
        )
        .order_by("-message_id")
        .values_list("message_id", flat=True)
        .first()
    )
    return int(latest_message_id or 0)


def _get_active_fight_encounter(scenario: Scenario):
    return FightEncounter.objects.filter(scenario=scenario, is_active=True).order_by('-started_at').first()


def _fight_effective_dex(character: Character, is_weapon_prepared: bool) -> int:
    base = max(0, character.dexterity)
    return base * 2 if is_weapon_prepared else base


def _sync_fight_participant_order(encounter: FightEncounter):
    participants = list(
        FightParticipant.objects.filter(encounter=encounter, is_active=True)
        .select_related('character')
        .order_by('-dexterity_with_bonus', '-character__dexterity', 'id')
    )
    for idx, participant in enumerate(participants, start=1):
        participant.initiative_order = idx
    if participants:
        FightParticipant.objects.bulk_update(participants, ['initiative_order'])
    return participants


def _serialize_fight_participant(scenario: Scenario, participant: FightParticipant, npc_display_name_map: dict[int, str]):
    sheet = _build_session_sheet(participant.character)
    display_name = npc_display_name_map.get(participant.character_id)
    if display_name:
        sheet['display_name'] = display_name

    card_html = render_to_string(
        'characters/_character_sheet.html',
        {
            'sheet': sheet,
            'sheet_id': f'fight-sheet-{participant.id}',
            'show_fight_extras': True,
            'show_notes': False,
            'notes_editable': False,
            'show_actions': False,
            'status_adjustable': True,
            'adjust_url': reverse('scenarios:character_adjust_stats', args=[scenario.id, participant.character.id]),
        },
    )

    return {
        'participant_id': participant.id,
        'character_id': participant.character.id,
        'display_name': display_name or participant.character.name,
        'is_npc': participant.character_id in npc_display_name_map,
        'is_alive': participant.character.is_alive,
        'is_weapon_prepared': participant.is_weapon_prepared,
        'dex_base': participant.character.dexterity,
        'dex_effective': participant.dexterity_with_bonus,
        'card_html': card_html,
    }


def _build_fight_state(scenario: Scenario):
    encounter = _get_active_fight_encounter(scenario)
    npc_display_name_map = {
        snpc.npc_id: snpc.get_display_name()
        for snpc in ScenarioNPC.objects.filter(scenario=scenario).select_related('npc')
    }

    participants = []
    active_character_ids = set()
    if encounter:
        ordered_participants = _sync_fight_participant_order(encounter)
        for participant in ordered_participants:
            participants.append(_serialize_fight_participant(scenario, participant, npc_display_name_map))
            active_character_ids.add(participant.character_id)

    available = []
    for sp in ScenarioPlayer.objects.filter(scenario=scenario, is_active=True).select_related('player', 'character'):
        if not sp.character or not sp.character.is_alive or sp.character_id in active_character_ids:
            continue
        available.append({
            'character_id': sp.character_id,
            'type': 'PC',
            'label': f"{sp.character.name} (PC) - {sp.player.username}",
        })

    for snpc in ScenarioNPC.objects.filter(scenario=scenario, is_active=True).select_related('npc'):
        if not snpc.npc or not snpc.npc.is_alive or snpc.npc_id in active_character_ids:
            continue
        available.append({
            'character_id': snpc.npc_id,
            'type': 'NPC',
            'label': f"{snpc.get_display_name()} (NPC)",
        })

    round_number = 0
    if encounter:
        round_number = max(1, encounter.round_number)

    return {
        'active': bool(encounter),
        'encounter_id': encounter.id if encounter else None,
        'round_number': round_number,
        'participants': participants,
        'available': available,
    }


# ---------------------------------------------------------------------------
# Scenario list / archive
# ---------------------------------------------------------------------------


@login_required
def scenario_list(request):
    """Scenarios the current user is involved in (active / not completed)."""
    active_statuses = ["PLANNING", "ACTIVE", "PAUSED"]
    as_player = Scenario.objects.filter(
        players__player=request.user,
        status__in=active_statuses,
    )
    as_keeper = Scenario.objects.filter(
        keeper=request.user,
        status__in=active_statuses,
    )
    public_discoverable = Scenario.objects.filter(
        visibility="PUBLIC",
        status__in=active_statuses,
    ).exclude(
        keeper=request.user,
    ).exclude(
        players__player=request.user,
    )
    all_active = (as_player | as_keeper | public_discoverable).distinct().order_by("-created_at")

    member_scenario_ids = set(
        ScenarioPlayer.objects.filter(
            player=request.user,
            is_active=True,
            scenario__status__in=active_statuses,
        ).values_list("scenario_id", flat=True)
    )
    member_scenario_ids.update(
        Scenario.objects.filter(keeper=request.user, status__in=active_statuses).values_list("id", flat=True)
    )

    return render(request, "scenarios/list.html", {
        "scenarios": all_active,
        "member_scenario_ids": member_scenario_ids,
    })


@login_required
def scenario_archive(request):
    """Completed scenarios the user participated in or kept."""
    as_player = Scenario.objects.filter(players__player=request.user, status="COMPLETED")
    as_keeper = Scenario.objects.filter(keeper=request.user, status="COMPLETED")
    all_done = (as_player | as_keeper).distinct().order_by("-ended_at", "-created_at")
    return render(request, "scenarios/archive.html", {"scenarios": all_done})


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@_keeper_required
def scenario_create(request):
    """Create a new scenario (Keeper / admin only)."""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, "Scenario name is required.")
            return render(request, "scenarios/create.html", {
                "form_data": request.POST,
                "status_choices": Scenario.STATUS_CHOICES,
                "visibility_choices": Scenario.VISIBILITY_CHOICES,
            })

        scenario = Scenario.objects.create(
            name=name,
            description=request.POST.get("description", ""),
            place=request.POST.get("place", ""),
            visibility=request.POST.get("visibility", "PRIVATE"),
            status=request.POST.get("status", "PLANNING"),
            keeper=request.user,
        )
        # Auto-generate the first invitation link
        invite_code = secrets.token_urlsafe(20)
        Invitation.objects.create(scenario=scenario, invited_by=request.user, invite_code=invite_code)

        messages.success(request, f"Scenario '{name}' created!")
        return redirect("scenarios:manage", scenario_id=scenario.id)

    return render(request, "scenarios/create.html", {
        "status_choices": Scenario.STATUS_CHOICES,
        "visibility_choices": Scenario.VISIBILITY_CHOICES,
    })


@_keeper_required
def scenario_edit(request, scenario_id):
    """Edit scenario metadata."""
    scenario = _get_scenario_for_keeper(request, scenario_id)

    if request.method == "POST":
        scenario.name = request.POST.get("name", scenario.name).strip() or scenario.name
        scenario.description = request.POST.get("description", scenario.description)
        scenario.place = request.POST.get("place", scenario.place)
        scenario.visibility = request.POST.get("visibility", scenario.visibility)
        new_status = request.POST.get("status", scenario.status)
        if new_status == "ACTIVE" and scenario.status != "ACTIVE":
            scenario.started_at = scenario.started_at or timezone.now()
        elif new_status == "COMPLETED" and scenario.status != "COMPLETED":
            scenario.ended_at = timezone.now()
        scenario.status = new_status
        scenario.save()
        messages.success(request, "Scenario updated.")
        return redirect("scenarios:manage", scenario_id=scenario.id)

    return render(request, "scenarios/edit.html", {
        "scenario": scenario,
        "status_choices": Scenario.STATUS_CHOICES,
        "visibility_choices": Scenario.VISIBILITY_CHOICES,
    })


@_keeper_required
def scenario_delete(request, scenario_id):
    """Delete scenario."""
    scenario = _get_scenario_for_keeper(request, scenario_id)
    if request.method == "POST":
        name = scenario.name
        scenario.delete()
        messages.success(request, f"Scenario '{name}' deleted.")
        return redirect("scenarios:list")
    return render(request, "scenarios/confirm_delete.html", {"scenario": scenario})


# ---------------------------------------------------------------------------
# Management page
# ---------------------------------------------------------------------------


@_keeper_required
def scenario_manage(request, scenario_id):
    """Main management page for a scenario (Keeper dashboard)."""
    scenario = _get_scenario_for_keeper(request, scenario_id)
    players = ScenarioPlayer.objects.filter(scenario=scenario).select_related("player", "character").prefetch_related(
        "character__skills__skill", "character__weapons__weapon", "character__items__item", "character__spells__spell"
    )
    npcs = ScenarioNPC.objects.filter(scenario=scenario).select_related("npc", "source_template").prefetch_related(
        "npc__skills__skill", "npc__weapons__weapon", "npc__items__item", "npc__spells__spell"
    )
    # Show only the single active (unused) invite link
    invitation = Invitation.objects.filter(scenario=scenario, is_used=False).order_by("-created_at").first()
    npc_templates = NPCTemplate.objects.all().order_by("name")

    # Build a JSON-serialisable list for the template-preview modal
    npc_templates_data = []
    for tpl in npc_templates:
        payload = tpl.payload if isinstance(tpl.payload, dict) else {}
        chars = payload.get("characteristics", {})
        status = payload.get("status", {})
        npc_templates_data.append({
            "id": tpl.id,
            "name": tpl.name,
            "description": payload.get("description", ""),
            "occupation": payload.get("character_info", {}).get("occupation", ""),
            "stats": {k: chars.get(k, 0) for k in ["STR", "CON", "DEX", "INT", "POW", "SIZ", "APP", "EDU"]},
            "hp_max": status.get("HP", {}).get("max", 0),
            "hp_current": status.get("HP", {}).get("current", 0),
            "mp_max": status.get("MP", {}).get("max", 0),
            "san_max": status.get("Sanity", {}).get("max", 0),
        })

    player_cards = []
    for sp in players:
        if not sp.character:
            continue
        player_cards.append({
            "sp": sp,
            "sheet": _build_session_sheet(sp.character),
            "sheet_id": f"pc-sheet-{sp.id}",
        })

    npc_cards = []
    for snpc in npcs:
        sheet = _build_session_sheet(snpc.npc)
        sheet["display_name"] = snpc.get_display_name()
        npc_cards.append({
            "snpc": snpc,
            "sheet": sheet,
            "sheet_id": f"npc-sheet-{snpc.id}",
        })

    return render(request, "scenarios/manage.html", {
        "scenario": scenario,
        "players": players,
        "npcs": npcs,
        "player_cards": player_cards,
        "npc_cards": npc_cards,
        "invitation": invitation,
        "npc_templates": npc_templates,
        "npc_templates_json": _json.dumps(npc_templates_data),
        "status_effects": StatusEffect.objects.all().order_by("effect_type", "name"),
        "status_choices": Scenario.STATUS_CHOICES,
        "visibility_choices": Scenario.VISIBILITY_CHOICES,
    })


# ---------------------------------------------------------------------------
# In-game time
# ---------------------------------------------------------------------------


@require_POST
@_keeper_required
def scenario_advance_time(request, scenario_id):
    scenario = _get_scenario_for_keeper(request, scenario_id)
    original_day = scenario.in_game_day or 1
    original_total_minutes = ((original_day - 1) * 1440) + (scenario.in_game_time.hour * 60) + scenario.in_game_time.minute
    try:
        minutes = int(request.POST.get("minutes", 0))
    except (ValueError, TypeError):
        minutes = 0
    days_crossed = 0
    hours_crossed = 0
    if minutes > 0:
        old_time = scenario.in_game_time
        new_time = old_time + timedelta(minutes=minutes)
        days_crossed = (new_time.date() - old_time.date()).days
        scenario.in_game_time = new_time
        if days_crossed > 0:
            scenario.in_game_day = (scenario.in_game_day or 1) + days_crossed
        new_day = scenario.in_game_day or 1
        new_total_minutes = ((new_day - 1) * 1440) + (new_time.hour * 60) + new_time.minute
        hours_crossed = max(0, (new_total_minutes // 60) - (original_total_minutes // 60))
        scenario.save(update_fields=["in_game_time", "in_game_day"])
        if hours_crossed > 0:
            apply_hourly_mp_restore(scenario, hours=hours_crossed)
        if days_crossed > 0:
            apply_daily_hp_restore(scenario, days=days_crossed)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        day_changed = (scenario.in_game_day or 1) != original_day
        should_refresh_cards = day_changed or hours_crossed > 0
        return JsonResponse({
            "ok": True,
            "in_game_time": scenario.in_game_time.strftime("%H:%M"),
            "in_game_day": scenario.in_game_day,
            "day_changed": day_changed,
            "updated_cards": _get_session_card_updates(scenario) if should_refresh_cards else [],
        })
    messages.success(request, f"In-game time advanced by {minutes} min.")
    return redirect("scenarios:manage", scenario_id=scenario.id)


@require_POST
@_keeper_required
def scenario_set_time(request, scenario_id):
    """Set the in-game time (HH:MM) and/or day number."""
    scenario = _get_scenario_for_keeper(request, scenario_id)
    original_day = scenario.in_game_day or 1
    original_minutes = scenario.in_game_time.hour * 60 + scenario.in_game_time.minute
    raw = request.POST.get("in_game_time", "").strip()
    if raw:
        from datetime import datetime as dt
        try:
            parts = raw.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Out of range")
            current = scenario.in_game_time
            naive = dt(
                year=current.year, month=current.month, day=current.day,
                hour=hour, minute=minute, second=0, microsecond=0,
            )
            if timezone.is_naive(naive):
                naive = timezone.make_aware(naive)
            scenario.in_game_time = naive
        except (ValueError, IndexError):
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": False, "error": "Invalid time format. Use HH:MM."}, status=400)
            messages.error(request, "Invalid time format. Use HH:MM.")
            return redirect("scenarios:manage", scenario_id=scenario.id)

    raw_day = request.POST.get("in_game_day", "").strip()
    if raw_day:
        try:
            day = int(raw_day)
            if day < 1:
                raise ValueError("Day must be ≥ 1")
            scenario.in_game_day = day
        except ValueError:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": False, "error": "Invalid day number."}, status=400)
            messages.error(request, "Invalid day number.")
            return redirect("scenarios:manage", scenario_id=scenario.id)

    scenario.save(update_fields=["in_game_time", "in_game_day"])
    new_day = scenario.in_game_day or 1
    new_minutes = scenario.in_game_time.hour * 60 + scenario.in_game_time.minute
    original_total_minutes = ((original_day - 1) * 1440) + original_minutes
    new_total_minutes = ((new_day - 1) * 1440) + new_minutes
    total_minutes_crossed = new_total_minutes - original_total_minutes
    hours_crossed = max(0, (new_total_minutes // 60) - (original_total_minutes // 60))
    days_crossed = max(0, new_day - original_day)

    if hours_crossed > 0:
        apply_hourly_mp_restore(scenario, hours=hours_crossed)
    if days_crossed > 0:
        apply_daily_hp_restore(scenario, days=days_crossed)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        day_changed = (scenario.in_game_day or 1) != original_day
        should_refresh_cards = day_changed or hours_crossed > 0
        return JsonResponse({
            "ok": True,
            "in_game_time": scenario.in_game_time.strftime("%H:%M"),
            "in_game_day": scenario.in_game_day,
            "day_changed": day_changed,
            "updated_cards": _get_session_card_updates(scenario) if should_refresh_cards else [],
        })
    messages.success(request, "In-game time updated.")
    return redirect("scenarios:manage", scenario_id=scenario.id)


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


@require_POST
@_keeper_required
def scenario_save_notes(request, scenario_id):
    scenario = _get_scenario_for_keeper(request, scenario_id)
    scenario.public_notes = request.POST.get("public_notes", scenario.public_notes)
    scenario.keeper_notes = request.POST.get("keeper_notes", scenario.keeper_notes)
    scenario.save(update_fields=["public_notes", "keeper_notes"])
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    messages.success(request, "Notes saved.")
    return redirect("scenarios:manage", scenario_id=scenario.id)


# ---------------------------------------------------------------------------
# Status quick-update
# ---------------------------------------------------------------------------


@require_POST
@_keeper_required
def scenario_update_status(request, scenario_id):
    scenario = _get_scenario_for_keeper(request, scenario_id)
    new_status = request.POST.get("status")
    valid_statuses = [s[0] for s in Scenario.STATUS_CHOICES]
    if new_status in valid_statuses:
        if new_status == "ACTIVE" and scenario.status != "ACTIVE":
            scenario.started_at = scenario.started_at or timezone.now()
        elif new_status == "COMPLETED" and scenario.status != "COMPLETED":
            scenario.ended_at = timezone.now()
        scenario.status = new_status
        scenario.save()
        messages.success(request, f"Status changed to {scenario.get_status_display()}.")
    else:
        messages.error(request, "Invalid status.")
    return redirect("scenarios:manage", scenario_id=scenario.id)


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


@require_POST
@_keeper_required
def scenario_invite_create(request, scenario_id):
    scenario = _get_scenario_for_keeper(request, scenario_id)
    invite_code = secrets.token_urlsafe(20)
    Invitation.objects.create(scenario=scenario, invited_by=request.user, invite_code=invite_code)
    messages.success(request, "Invitation link created.")
    return redirect("scenarios:manage", scenario_id=scenario.id)


@require_POST
@_keeper_required
def scenario_invite_revoke(request, scenario_id, invite_id):
    scenario = _get_scenario_for_keeper(request, scenario_id)
    invitation = get_object_or_404(Invitation, id=invite_id, scenario=scenario)
    invitation.delete()
    messages.success(request, "Invitation revoked.")
    return redirect("scenarios:manage", scenario_id=scenario.id)
# ---------------------------------------------------------------------------
# NPC management
# ---------------------------------------------------------------------------


@require_POST
@_keeper_required
def scenario_player_remove(request, scenario_id, player_id):
    scenario = _get_scenario_for_keeper(request, scenario_id)
    sp = get_object_or_404(ScenarioPlayer, scenario=scenario, player_id=player_id)
    sp.delete()
    messages.success(request, "Player removed from scenario.")
    return redirect("scenarios:manage", scenario_id=scenario.id)


@require_POST
@_keeper_required
def scenario_player_unassign_character(request, scenario_id, player_id):
    """Keeper: clear a player's character slot without removing them from the scenario."""
    scenario = _get_scenario_for_keeper(request, scenario_id)
    sp = get_object_or_404(ScenarioPlayer, scenario=scenario, player_id=player_id)
    char_name = sp.character.name if sp.character else None
    sp.character = None
    sp.save(update_fields=["character"])
    if char_name:
        messages.success(request, f"Character '{char_name}' removed from {sp.player.username}'s slot.")
    else:
        messages.info(request, "Slot was already empty.")
    return redirect("scenarios:manage", scenario_id=scenario.id)


@login_required
def scenario_player_select_character(request, scenario_id):
    """Player: pick a (new) character for their slot — allowed when slot is empty or character is dead."""
    scenario = get_object_or_404(Scenario, id=scenario_id)
    sp = get_object_or_404(ScenarioPlayer, scenario=scenario, player=request.user)

    # Guard: character still alive → no replacement
    if sp.character and sp.character.is_alive:
        messages.error(request, "Your character is still alive and cannot be replaced.")
        return redirect("scenarios:detail", scenario_id=scenario.id)

    if request.method == "POST":
        character_id = request.POST.get("character_id")
        character = get_object_or_404(
            Character, id=character_id, owner=request.user,
            is_alive=True, character_type="PC",
        )
        sp.character = character
        sp.save(update_fields=["character"])
        messages.success(request, f"Now playing as {character.name}.")
        return redirect("scenarios:detail", scenario_id=scenario.id)

    available_chars = Character.objects.filter(owner=request.user, is_alive=True, character_type="PC")
    return render(request, "scenarios/select_character.html", {
        "scenario": scenario,
        "available_characters": available_chars,
        "dead_character": sp.character,
    })


# ---------------------------------------------------------------------------
# In-session stat & alive management
# ---------------------------------------------------------------------------

@require_POST
@_keeper_required
def scenario_character_adjust_stats(request, scenario_id, character_id):
    """Keeper: AJAX update of HP/MP/SAN/LCK for any character in the session."""
    scenario = _get_scenario_for_keeper(request, scenario_id)
    character = get_object_or_404(Character, id=character_id)

    # Security: character must actually be in this scenario
    in_as_pc = ScenarioPlayer.objects.filter(scenario=scenario, character=character).exists()
    in_as_npc = ScenarioNPC.objects.filter(scenario=scenario, npc=character).exists()
    if not (in_as_pc or in_as_npc):
        return JsonResponse({"ok": False, "error": "Character not in scenario"}, status=403)

    fields = []
    for key, attr, max_attr in [
        ("hp",      "hp_current",      "hp_max"),
        ("mp",      "mp_current",      "mp_max"),
        ("sanity",  "sanity_current",  "sanity_max"),
        ("luck",    "luck",            None),
    ]:
        if key in request.POST:
            try:
                val = int(request.POST[key])
            except (ValueError, TypeError):
                continue
            mx = getattr(character, max_attr) if max_attr else 100
            val = max(0, min(val, mx))
            setattr(character, attr, val)
            fields.append(attr)

    if fields:
        character.save(update_fields=fields)

    return JsonResponse({
        "ok": True,
        "hp_current": character.hp_current,
        "hp_max": character.hp_max,
        "mp_current": character.mp_current,
        "mp_max": character.mp_max,
        "sanity_current": character.sanity_current,
        "sanity_max": character.sanity_max,
        "luck": character.luck,
        "is_alive": character.is_alive,
    })


@require_POST
@_keeper_required
def scenario_character_toggle_alive(request, scenario_id, character_id):
    """Keeper: explicitly mark a character as dead or alive."""
    scenario = _get_scenario_for_keeper(request, scenario_id)
    character = get_object_or_404(Character, id=character_id)

    in_as_pc = ScenarioPlayer.objects.filter(scenario=scenario, character=character).exists()
    in_as_npc = ScenarioNPC.objects.filter(scenario=scenario, npc=character).exists()
    if not (in_as_pc or in_as_npc):
        return JsonResponse({"ok": False, "error": "Character not in scenario"}, status=403)

    character.is_alive = not character.is_alive
    character.save(update_fields=["is_alive"])
    return JsonResponse({"ok": True, "is_alive": character.is_alive})


@require_POST
@_keeper_required
def scenario_character_skill_needs_update(request, scenario_id, character_id, skill_id):
    """Keeper: toggle needs_update flag on a character's skill."""
    scenario = _get_scenario_for_keeper(request, scenario_id)
    character = get_object_or_404(Character, id=character_id)
    if not ScenarioPlayer.objects.filter(scenario=scenario, character=character).exists():
        return JsonResponse({"ok": False, "error": "Character not in scenario"}, status=403)
    char_skill, _ = CharacterSkill.objects.get_or_create(
        character=character,
        skill_id=skill_id,
        defaults={"value": 0},
    )
    char_skill.needs_update = not char_skill.needs_update
    char_skill.save(update_fields=["needs_update"])
    return JsonResponse({"ok": True, "needs_update": char_skill.needs_update})


# ---------------------------------------------------------------------------
# NPC management
# ---------------------------------------------------------------------------





@require_POST
@_keeper_required
def scenario_npc_create(request, scenario_id):
    """Create a brand-new NPC and add it to the scenario."""
    scenario = _get_scenario_for_keeper(request, scenario_id)
    name = request.POST.get("npc_name", "").strip()
    if not name:
        messages.error(request, "NPC name is required.")
        return redirect("scenarios:manage", scenario_id=scenario.id)

    npc_str = int(request.POST.get("npc_str", 50) or 50)
    npc_con = int(request.POST.get("npc_con", 50) or 50)
    npc_pow = int(request.POST.get("npc_pow", 50) or 50)
    hp = max((npc_str + npc_con) // 10, 1)
    mp = max(npc_pow // 5, 1)
    san = npc_pow
    npc = Character.objects.create(
        owner=request.user,
        character_type="NPC",
        name=name,
        occupation=request.POST.get("npc_occupation", ""),
        description=request.POST.get("npc_description", ""),
        strength=npc_str,
        constitution=npc_con,
        dexterity=int(request.POST.get("npc_dex", 50) or 50),
        intelligence=int(request.POST.get("npc_int", 50) or 50),
        power=npc_pow,
        size=int(request.POST.get("npc_siz", 50) or 50),
        appearance=int(request.POST.get("npc_app", 50) or 50),
        education=int(request.POST.get("npc_edu", 50) or 50),
        hp_current=hp,
        hp_max=hp,
        mp_current=mp,
        mp_max=mp,
        sanity_current=san,
        sanity_max=99,
        sanity_start=san,
        luck=int(request.POST.get("npc_pow", 50) or 50),
        movement=8,
        build=0,
        damage_bonus="0",
        cash=0,
    )
    ScenarioNPC.objects.create(scenario=scenario, npc=npc)
    messages.success(request, f"NPC '{name}' created and added.")
    return redirect("scenarios:manage", scenario_id=scenario.id)


@require_POST
@_keeper_required
def scenario_npc_from_template(request, scenario_id):
    """Add an NPC created from an NPCTemplate."""
    scenario = _get_scenario_for_keeper(request, scenario_id)
    template = get_object_or_404(NPCTemplate, id=request.POST.get("template_id"))
    display_name = request.POST.get("display_name", "").strip()
    npc = _npc_from_template(template, request.user, display_name)
    ScenarioNPC.objects.create(
        scenario=scenario,
        npc=npc,
        display_name=display_name,
        source_template=template,
    )
    messages.success(request, f"NPC '{npc.name}' added from template '{template.name}'.")
    return redirect("scenarios:manage", scenario_id=scenario.id)


@require_POST
@_keeper_required
def scenario_npc_clone(request, scenario_id, snpc_id):
    """Clone an existing scenario NPC (creates an independent Character copy)."""
    scenario = _get_scenario_for_keeper(request, scenario_id)
    original_snpc = get_object_or_404(ScenarioNPC, id=snpc_id, scenario=scenario)
    base_name = original_snpc.display_name or original_snpc.npc.name
    root_name = base_name.split(" #")[0]
    # Count all scenario NPCs whose character name starts with the root name
    existing_count = ScenarioNPC.objects.filter(
        scenario=scenario,
        npc__name__startswith=root_name,
    ).count()
    clone_name = f"{root_name} #{existing_count + 1}"
    cloned_char = _clone_npc_character(original_snpc.npc, clone_name)
    ScenarioNPC.objects.create(
        scenario=scenario,
        npc=cloned_char,
        display_name=clone_name,
        source_template=original_snpc.source_template,
    )
    messages.success(request, f"Cloned NPC as '{clone_name}'.")
    return redirect("scenarios:manage", scenario_id=scenario.id)


@require_POST
@_keeper_required
def scenario_npc_remove(request, scenario_id, snpc_id):
    """Remove an NPC entry from a scenario."""
    scenario = _get_scenario_for_keeper(request, scenario_id)
    snpc = get_object_or_404(ScenarioNPC, id=snpc_id, scenario=scenario)
    name = snpc.get_display_name()
    snpc.delete()
    messages.success(request, f"NPC '{name}' removed from scenario.")
    return redirect("scenarios:manage", scenario_id=scenario.id)


# ---------------------------------------------------------------------------
# Player-facing views
# ---------------------------------------------------------------------------


@login_required
def scenario_detail(request, scenario_id):
    """Display scenario page to a player."""
    scenario = get_object_or_404(Scenario, id=scenario_id)
    is_keeper = scenario.keeper == request.user or request.user.is_staff
    scenario_player = None

    if not is_keeper:
        try:
            scenario_player = ScenarioPlayer.objects.get(scenario=scenario, player=request.user)
        except ScenarioPlayer.DoesNotExist:
            if scenario.visibility == "PUBLIC" and scenario.status in {"PLANNING", "ACTIVE", "PAUSED"}:
                return redirect("scenarios:public_join", scenario_id=scenario.id)
            messages.error(request, "You are not a participant in this scenario.")
            return redirect("scenarios:list")

    character = scenario_player.character if scenario_player else None
    character_sheet = _build_session_sheet(character) if character else None

    # Provide available characters when the player needs to pick one
    available_characters = []
    if scenario_player and (not character or not character.is_alive):
        available_characters = list(
            Character.objects.filter(owner=request.user, is_alive=True, character_type="PC")
        )

    player_hints = []
    if not is_keeper:
        player_hints = list(
            Hint.objects.filter(audience=Hint.AUDIENCE_PLAYER, is_active=True)
            .order_by('sort_order', 'id')
        )

    return render(request, "scenarios/detail.html", {
        "scenario": scenario,
        "character": character,
        "character_sheet": character_sheet,
        "is_keeper": is_keeper,
        "unread_messages": _get_unread_message_count(scenario, request.user) if not is_keeper else 0,
        "unread_private_message_id": _get_latest_unread_private_message_id(scenario, request.user) if not is_keeper else 0,
        "scenario_player": scenario_player,
        "available_characters": available_characters,
        "player_hints": player_hints,
    })


@_keeper_required
def scenario_keeper_hints(request, scenario_id):
    """Dedicated page with all keeper hints for quick reference."""
    scenario = _get_scenario_for_keeper(request, scenario_id)
    keeper_hints = Hint.objects.filter(audience=Hint.AUDIENCE_KEEPER, is_active=True).order_by('sort_order', 'id')
    return render(request, 'scenarios/keeper_hints.html', {
        'scenario': scenario,
        'keeper_hints': keeper_hints,
    })


@login_required
def scenario_player_snapshot(request, scenario_id):
    """Player polling endpoint for live time/sheet/public-notes updates."""
    scenario = get_object_or_404(Scenario, id=scenario_id)
    is_keeper = scenario.keeper == request.user or request.user.is_staff
    scenario_player = None

    if not is_keeper:
        scenario_player = get_object_or_404(ScenarioPlayer, scenario=scenario, player=request.user)

    character = scenario_player.character if scenario_player else None
    sheet_payload = None
    if character and character.is_alive:
        sheet = _build_session_sheet(character)
        sheet_payload = {
            "summary": {
                "name": character.name,
                "occupation": character.occupation or "",
            },
            "character": {
                "name": sheet.get("display_name") or character.name,
                "description": character.description or "",
                "cash": int(character.cash or 0),
            },
            "resources": {
                "hp": {"current": character.hp_current, "max": character.hp_max},
                "sanity": {"current": character.sanity_current, "max": character.sanity_max},
                "mp": {"current": character.mp_current, "max": character.mp_max},
                "luck": {"current": character.luck, "max": 100},
            },
            "stats": {
                "strength": character.strength,
                "constitution": character.constitution,
                "dexterity": character.dexterity,
                "intelligence": character.intelligence,
                "power": character.power,
                "size": character.size,
                "appearance": character.appearance,
                "education": character.education,
            },
            "skills": [dict(s, name=_t(s["name"])) for s in sheet.get("skills", [])],
            "default_skills": [dict(s, name=_t(s["name"])) for s in sheet.get("default_skills", [])],
            "combat_skills": [dict(s, name=_t(s["name"])) for s in sheet.get("combat_skills", [])],
            "weapons": sheet.get("weapons", []),
            "items": sheet.get("items", []),
            "spells": sheet.get("spells", []),
            "dodge_value": sheet.get("dodge_value", 0),
            "can_add_custom_skill": bool(sheet.get("can_add_custom_skill", False)),
        }

    return JsonResponse({
        "ok": True,
        "day": scenario.in_game_day,
        "time": scenario.in_game_time.strftime("%H:%M"),
        "public_notes": scenario.public_notes,
        "unread_messages": _get_unread_message_count(scenario, request.user) if not is_keeper else 0,
        "latest_unread_private_message_id": _get_latest_unread_private_message_id(scenario, request.user) if not is_keeper else 0,
        "has_alive_character": bool(character and character.is_alive),
        "sheet": sheet_payload,
    })


@require_POST
@login_required
def scenario_player_save_private_notes(request, scenario_id):
    """Save session-private notes for the current player."""
    scenario = get_object_or_404(Scenario, id=scenario_id)
    scenario_player = get_object_or_404(ScenarioPlayer, scenario=scenario, player=request.user)
    scenario_player.private_notes = request.POST.get("private_notes", "")
    scenario_player.save(update_fields=["private_notes"])
    return JsonResponse({"ok": True})


@login_required
def join_scenario(request, invite_code):
    """Join a scenario via invitation link."""
    try:
        invitation = Invitation.objects.get(invite_code=invite_code, is_used=False)
    except Invitation.DoesNotExist:
        messages.error(request, "Invalid or expired invitation.")
        return redirect("dashboard")

    scenario = invitation.scenario

    if ScenarioPlayer.objects.filter(scenario=scenario, player=request.user).exists():
        messages.info(request, "You are already participating in this scenario.")
        return redirect("scenarios:detail", scenario_id=scenario.id)

    if request.method == "POST":
        character_id = request.POST.get("character_id")
        if character_id:
            character = get_object_or_404(Character, id=character_id, owner=request.user, is_alive=True)
            ScenarioPlayer.objects.create(scenario=scenario, player=request.user, character=character)
            invitation.is_used = True
            invitation.used_at = timezone.now()
            invitation.save()
            messages.success(request, f"Joined '{scenario.name}' with {character.name}!")
            return redirect("scenarios:detail", scenario_id=scenario.id)

    available_chars = Character.objects.filter(owner=request.user, is_alive=True, character_type="PC")
    return render(request, "scenarios/join.html", {
        "scenario": scenario,
        "available_characters": available_chars,
    })


@login_required
def join_public_scenario(request, scenario_id):
    """Join a public scenario without an invitation link."""
    scenario = get_object_or_404(
        Scenario,
        id=scenario_id,
        visibility="PUBLIC",
        status__in=["PLANNING", "ACTIVE", "PAUSED"],
    )

    is_keeper = scenario.keeper == request.user or request.user.is_staff
    if is_keeper:
        return redirect("scenarios:detail", scenario_id=scenario.id)

    if ScenarioPlayer.objects.filter(scenario=scenario, player=request.user).exists():
        messages.info(request, "You are already participating in this scenario.")
        return redirect("scenarios:detail", scenario_id=scenario.id)

    if request.method == "POST":
        character_id = request.POST.get("character_id")
        if character_id:
            character = get_object_or_404(
                Character,
                id=character_id,
                owner=request.user,
                is_alive=True,
                character_type="PC",
            )
            ScenarioPlayer.objects.create(scenario=scenario, player=request.user, character=character)
            messages.success(request, f"Joined '{scenario.name}' with {character.name}!")
            return redirect("scenarios:detail", scenario_id=scenario.id)
        messages.error(request, "Please choose a character to join.")

    available_chars = Character.objects.filter(owner=request.user, is_alive=True, character_type="PC")
    return render(request, "scenarios/join.html", {
        "scenario": scenario,
        "available_characters": available_chars,
    })


# ---------------------------------------------------------------------------
# Fight encounter
# ---------------------------------------------------------------------------


@login_required
def fight_encounter(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id, keeper=request.user)
    encounter = FightEncounter.objects.filter(scenario=scenario, is_active=True).first()
    if not encounter and request.method == "POST":
        encounter = FightEncounter.objects.create(scenario=scenario)
        messages.success(request, "Fight encounter started!")
    return render(request, "scenarios/fight.html", {"scenario": scenario, "encounter": encounter})


@_keeper_required
def scenario_fight_state(request, scenario_id):
    scenario = _get_scenario_for_keeper(request, scenario_id)
    return JsonResponse({"ok": True, **_build_fight_state(scenario)})


@require_POST
@_keeper_required
def scenario_fight_start(request, scenario_id):
    scenario = _get_scenario_for_keeper(request, scenario_id)
    encounter = _get_active_fight_encounter(scenario)
    if not encounter:
        encounter = FightEncounter.objects.create(scenario=scenario, is_active=True)
    return JsonResponse({"ok": True, **_build_fight_state(scenario)})


@require_POST
@_keeper_required
def scenario_fight_end(request, scenario_id):
    scenario = _get_scenario_for_keeper(request, scenario_id)
    encounter = _get_active_fight_encounter(scenario)
    if encounter:
        FightParticipant.objects.filter(encounter=encounter).delete()
        encounter.is_active = False
        encounter.ended_at = timezone.now()
        encounter.save(update_fields=['is_active', 'ended_at'])
    return JsonResponse({"ok": True, **_build_fight_state(scenario)})


@require_POST
@_keeper_required
def scenario_fight_add_participant(request, scenario_id):
    scenario = _get_scenario_for_keeper(request, scenario_id)
    encounter = _get_active_fight_encounter(scenario) or FightEncounter.objects.create(scenario=scenario, is_active=True)

    try:
        character_id = int(request.POST.get('character_id', 0))
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Invalid character id."}, status=400)

    character = get_object_or_404(Character, id=character_id)
    in_as_pc = ScenarioPlayer.objects.filter(scenario=scenario, character=character, is_active=True).exists()
    in_as_npc = ScenarioNPC.objects.filter(scenario=scenario, npc=character, is_active=True).exists()
    if not (in_as_pc or in_as_npc):
        return JsonResponse({"ok": False, "error": "Character not in this scenario."}, status=403)

    participant, created = FightParticipant.objects.get_or_create(
        encounter=encounter,
        character=character,
        defaults={
            'initiative_order': 999,
            'is_active': True,
            'is_weapon_prepared': False,
            'dexterity_with_bonus': _fight_effective_dex(character, False),
        },
    )
    if not created and not participant.is_active:
        participant.is_active = True
        participant.is_weapon_prepared = False
        participant.dexterity_with_bonus = _fight_effective_dex(character, False)
        participant.save(update_fields=['is_active', 'is_weapon_prepared', 'dexterity_with_bonus'])

    _sync_fight_participant_order(encounter)
    return JsonResponse({"ok": True, **_build_fight_state(scenario)})


@require_POST
@_keeper_required
def scenario_fight_remove_participant(request, scenario_id, participant_id):
    scenario = _get_scenario_for_keeper(request, scenario_id)
    encounter = _get_active_fight_encounter(scenario)
    if encounter:
        FightParticipant.objects.filter(encounter=encounter, id=participant_id).delete()
        _sync_fight_participant_order(encounter)
    return JsonResponse({"ok": True, **_build_fight_state(scenario)})


@require_POST
@_keeper_required
def scenario_fight_set_prepared(request, scenario_id, participant_id):
    scenario = _get_scenario_for_keeper(request, scenario_id)
    encounter = _get_active_fight_encounter(scenario)
    if not encounter:
        return JsonResponse({"ok": False, "error": "No active encounter."}, status=400)

    participant = get_object_or_404(FightParticipant, id=participant_id, encounter=encounter)
    is_prepared = request.POST.get('is_prepared') in {'1', 'true', 'True', 'on'}
    participant.is_weapon_prepared = is_prepared
    participant.dexterity_with_bonus = _fight_effective_dex(participant.character, is_prepared)
    participant.save(update_fields=['is_weapon_prepared', 'dexterity_with_bonus'])
    _sync_fight_participant_order(encounter)

    return JsonResponse({"ok": True, **_build_fight_state(scenario)})


@require_POST
@_keeper_required
def scenario_fight_advance_turn(request, scenario_id):
    scenario = _get_scenario_for_keeper(request, scenario_id)
    encounter = _get_active_fight_encounter(scenario)
    if not encounter:
        return JsonResponse({"ok": False, "error": "No active encounter."}, status=400)

    encounter.round_number = max(1, encounter.round_number) + 1
    encounter.current_turn_index = 0
    encounter.save(update_fields=['current_turn_index', 'round_number'])

    return JsonResponse({"ok": True, **_build_fight_state(scenario)})


@require_POST
@_keeper_required
def scenario_fight_reset_turns(request, scenario_id):
    scenario = _get_scenario_for_keeper(request, scenario_id)
    encounter = _get_active_fight_encounter(scenario)
    if not encounter:
        return JsonResponse({"ok": False, "error": "No active encounter."}, status=400)

    encounter.current_turn_index = 0
    encounter.round_number = 1
    encounter.save(update_fields=['current_turn_index', 'round_number'])

    return JsonResponse({"ok": True, **_build_fight_state(scenario)})


# ---------------------------------------------------------------------------
# Messaging system
# ---------------------------------------------------------------------------


@require_POST
@_keeper_required
def scenario_send_message(request, scenario_id):
    """Keeper sends a private message to a player in this scenario."""
    scenario = _get_scenario_for_keeper(request, scenario_id)
    content = request.POST.get("content", "").strip()
    recipient_id = request.POST.get("recipient_id")

    if not content:
        return JsonResponse({"ok": False, "error": "Message cannot be empty"}, status=400)

    if not recipient_id:
        return JsonResponse({"ok": False, "error": "Recipient is required."}, status=400)

    recipient_sp = ScenarioPlayer.objects.filter(
        scenario=scenario,
        player_id=recipient_id,
        is_active=True,
    ).select_related("player").first()
    if not recipient_sp:
        return JsonResponse({"ok": False, "error": "Recipient not in scenario"}, status=404)

    recipient = recipient_sp.player
    if recipient.id == request.user.id:
        return JsonResponse({"ok": False, "error": "Cannot send a private message to yourself."}, status=400)

    msg = Message.objects.create(
        scenario=scenario,
        sender=request.user,
        recipient=recipient,
        message_type="PRIVATE",
        content=content,
    )
    _create_message_receipts(msg)

    return JsonResponse({
        "ok": True,
        "message_id": msg.id,
        "sent_at": msg.sent_at.isoformat(),
        "message": _serialize_message(msg),
    })


@login_required
def scenario_get_messages(request, scenario_id):
    """Get messages for player (polling endpoint) - JSON only"""
    scenario = get_object_or_404(Scenario, id=scenario_id)

    # Security check
    is_keeper = scenario.keeper == request.user or request.user.is_staff
    if not is_keeper:
        try:
            ScenarioPlayer.objects.get(scenario=scenario, player=request.user)
        except ScenarioPlayer.DoesNotExist:
            return JsonResponse({"ok": False, "error": "Not participant"}, status=403)

    if is_keeper:
        latest_messages = Message.objects.filter(scenario=scenario).select_related("sender", "recipient")[:30]
        messages_list = [_serialize_message(message) for message in latest_messages]
        unread_count = 0
    else:
        receipts = list(
            MessageReceipt.objects.filter(
                message__scenario=scenario,
                user=request.user,
            ).select_related("message__sender", "message__recipient")[:30]
        )
        unread_count = sum(1 for receipt in receipts if receipt.read_at is None)
        messages_list = [_serialize_message(receipt.message, receipt) for receipt in receipts]

    return JsonResponse({
        "ok": True,
        "unread_count": unread_count,
        "messages": messages_list,
    })


@require_POST
@login_required
def scenario_mark_messages_read(request, scenario_id):
    """Mark the current player's scenario messages as read."""
    scenario = get_object_or_404(Scenario, id=scenario_id)
    is_keeper = scenario.keeper == request.user or request.user.is_staff
    if is_keeper:
        return JsonResponse({"ok": True, "marked_read": 0})

    get_object_or_404(ScenarioPlayer, scenario=scenario, player=request.user)
    updated = MessageReceipt.objects.filter(
        message__scenario=scenario,
        user=request.user,
        read_at__isnull=True,
    ).update(read_at=timezone.now())
    return JsonResponse({"ok": True, "marked_read": updated})


# ---------------------------------------------------------------------------
# Status effects management
# ---------------------------------------------------------------------------


@require_POST
@_keeper_required
def scenario_character_add_effect(request, scenario_id, character_id):
    """Keeper: Add a status effect, phobia, madness, or mania to a character."""
    from scenarios.services import add_status_effect

    scenario = _get_scenario_for_keeper(request, scenario_id)
    character = get_object_or_404(Character, id=character_id)

    # Security: character must be in this scenario
    in_as_pc = ScenarioPlayer.objects.filter(scenario=scenario, character=character).exists()
    in_as_npc = ScenarioNPC.objects.filter(scenario=scenario, npc=character).exists()
    if not (in_as_pc or in_as_npc):
        return JsonResponse({"ok": False, "error": "Character not in scenario"}, status=403)

    effect_id = request.POST.get("effect_id")
    effect_name = request.POST.get("effect_name")  # For custom effects
    remaining_rounds = request.POST.get("remaining_rounds", 1)

    try:
        remaining_rounds = int(remaining_rounds)
    except (ValueError, TypeError):
        remaining_rounds = 1

    # Get or create effect
    if effect_id:
        status_effect = get_object_or_404(StatusEffect, id=effect_id)
    elif effect_name:
        status_effect, _ = StatusEffect.objects.get_or_create(
            name=effect_name,
            defaults={
                'effect_type': 'NORMAL',
                'description': f'Custom effect: {effect_name}',
            }
        )
    else:
        return JsonResponse({"ok": False, "error": "Effect ID or name required"}, status=400)

    cse = add_status_effect(character, status_effect, remaining_rounds)

    return JsonResponse({
        "ok": True,
        "effect_id": cse.id,
        "effect_name": status_effect.name,
    })


@require_POST
@_keeper_required
def scenario_character_remove_effect(request, scenario_id, character_id, effect_id):
    """Keeper: Remove a status effect from a character."""
    from scenarios.services import remove_status_effect

    scenario = _get_scenario_for_keeper(request, scenario_id)
    character = get_object_or_404(Character, id=character_id)

    # Security: character must be in this scenario
    in_as_pc = ScenarioPlayer.objects.filter(scenario=scenario, character=character).exists()
    in_as_npc = ScenarioNPC.objects.filter(scenario=scenario, npc=character).exists()
    if not (in_as_pc or in_as_npc):
        return JsonResponse({"ok": False, "error": "Character not in scenario"}, status=403)

    status_effect = get_object_or_404(StatusEffect, id=effect_id)

    # Check if character has this effect
    cse = CharacterStatusEffect.objects.filter(
        character=character,
        status_effect=status_effect
    ).first()

    if not cse:
        return JsonResponse({"ok": False, "error": "Effect not on character"}, status=404)

    remove_status_effect(character, status_effect)

    return JsonResponse({"ok": True})


@login_required
def scenario_character_get_effects(request, scenario_id, character_id):
    """Get all status effects for a character - JSON only"""
    from scenarios.services import get_character_status_effects_display

    scenario = get_object_or_404(Scenario, id=scenario_id)
    character = get_object_or_404(Character, id=character_id)

    # Security check
    is_keeper = scenario.keeper == request.user or request.user.is_staff
    if not is_keeper:
        sp = get_object_or_404(ScenarioPlayer, scenario=scenario, player=request.user)
        if sp.character != character:
            return JsonResponse({"ok": False, "error": "Can only view own character"}, status=403)

    effects = get_character_status_effects_display(character)

    return JsonResponse({
        "ok": True,
        "character_id": character.id,
        "character_name": character.name,
        "effects": effects,
    })


# ---------------------------------------------------------------------------
# Update snapshot API to return JSON-only format
# ---------------------------------------------------------------------------


@login_required
def scenario_player_snapshot_json(request, scenario_id):
    """
    Player polling endpoint for live updates (static JSON payload, no HTML).
    Returns: day, time, public_notes, unread message count, character status.
    """
    from scenarios.services import get_character_status_effects_display

    scenario = get_object_or_404(Scenario, id=scenario_id)
    is_keeper = scenario.keeper == request.user or request.user.is_staff
    scenario_player = None

    if not is_keeper:
        scenario_player = get_object_or_404(ScenarioPlayer, scenario=scenario, player=request.user)

    character = scenario_player.character if scenario_player else None

    unread_count = _get_unread_message_count(scenario, request.user) if not is_keeper else 0

    # Build character summary
    character_data = None
    if character and character.is_alive:
        effects = get_character_status_effects_display(character)
        character_data = {
            "id": character.id,
            "name": character.name,
            "description": character.description or "",
            "occupation": character.occupation or "",
            "hp": {
                "current": character.hp_current,
                "max": character.hp_max,
            },
            "sanity": {
                "current": character.sanity_current,
                "max": character.sanity_max,
            },
            "mp": {
                "current": character.mp_current,
                "max": character.mp_max,
            },
            "luck": character.luck,
            "status_effects": effects,
        }

    return JsonResponse({
        "ok": True,
        "day": scenario.in_game_day,
        "time": scenario.in_game_time.strftime("%H:%M"),
        "public_notes": scenario.public_notes,
        "unread_messages": unread_count,
        "has_alive_character": bool(character and character.is_alive),
        "character": character_data,
    })
