from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Scenario, ScenarioPlayer, Invitation, FightEncounter


@login_required
def scenario_list(request):
    """List ongoing scenarios for current user"""
    scenarios = Scenario.objects.filter(
        players__player=request.user,
        status__in=['PLANNING', 'ACTIVE', 'PAUSED']
    ).distinct()

    return render(request, 'scenarios/list.html', {'scenarios': scenarios})


@login_required
def scenario_detail(request, scenario_id):
    """Display scenario for player"""
    scenario = get_object_or_404(Scenario, id=scenario_id)

    # Check if user is participant
    try:
        scenario_player = ScenarioPlayer.objects.get(
            scenario=scenario,
            player=request.user
        )
    except ScenarioPlayer.DoesNotExist:
        messages.error(request, "You are not a participant in this scenario.")
        return redirect('scenarios:list')

    context = {
        'scenario': scenario,
        'character': scenario_player.character,
        'is_keeper': scenario.keeper == request.user,
    }

    return render(request, 'scenarios/detail.html', context)


@login_required
def scenario_manage(request, scenario_id):
    """Scenario management page (keeper only)"""
    scenario = get_object_or_404(Scenario, id=scenario_id, keeper=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_time':
            time_delta = int(request.POST.get('time_delta', 0))
            scenario.in_game_time = timezone.now() + timezone.timedelta(minutes=time_delta)
            scenario.save()
            messages.success(request, f"Game time updated by {time_delta} minutes.")

        elif action == 'update_notes':
            scenario.public_notes = request.POST.get('public_notes', '')
            scenario.keeper_notes = request.POST.get('keeper_notes', '')
            scenario.save()
            messages.success(request, "Notes updated.")

    context = {
        'scenario': scenario,
        'players': ScenarioPlayer.objects.filter(scenario=scenario),
    }

    return render(request, 'scenarios/manage.html', context)


@login_required
def fight_encounter(request, scenario_id):
    """Fight encounter page (keeper only)"""
    scenario = get_object_or_404(Scenario, id=scenario_id, keeper=request.user)

    encounter = FightEncounter.objects.filter(
        scenario=scenario,
        is_active=True
    ).first()

    if not encounter and request.method == 'POST':
        # Create new encounter
        encounter = FightEncounter.objects.create(scenario=scenario)
        messages.success(request, "Fight encounter started!")

    context = {
        'scenario': scenario,
        'encounter': encounter,
    }

    return render(request, 'scenarios/fight.html', context)


@login_required
def scenario_create(request):
    """Create new scenario (keeper only)"""
    if not request.user.is_keeper():
        messages.error(request, "Only keepers can create scenarios.")
        return redirect('dashboard')

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')

        scenario = Scenario.objects.create(
            name=name,
            description=description,
            keeper=request.user
        )

        messages.success(request, f"Scenario '{name}' created successfully!")
        return redirect('scenarios:manage', scenario_id=scenario.id)

    return render(request, 'scenarios/create.html')


@login_required
def join_scenario(request, invite_code):
    """Join scenario via invitation link"""
    try:
        invitation = Invitation.objects.get(
            invite_code=invite_code,
            is_used=False
        )
    except Invitation.DoesNotExist:
        messages.error(request, "Invalid or expired invitation.")
        return redirect('dashboard')

    scenario = invitation.scenario

    # Check if already joined
    if ScenarioPlayer.objects.filter(scenario=scenario, player=request.user).exists():
        messages.info(request, "You are already participating in this scenario.")
        return redirect('scenarios:detail', scenario_id=scenario.id)

    if request.method == 'POST':
        character_id = request.POST.get('character_id')
        if character_id:
            from characters.models import Character
            character = get_object_or_404(
                Character,
                id=character_id,
                owner=request.user,
                is_alive=True
            )

            ScenarioPlayer.objects.create(
                scenario=scenario,
                player=request.user,
                character=character
            )

            invitation.is_used = True
            invitation.used_at = timezone.now()
            invitation.save()

            messages.success(request, f"Joined scenario '{scenario.name}' with {character.name}!")
            return redirect('scenarios:detail', scenario_id=scenario.id)

    # Get user's available characters
    from characters.models import Character
    available_characters = Character.objects.filter(
        owner=request.user,
        is_alive=True,
        character_type='PC'
    )

    context = {
        'scenario': scenario,
        'available_characters': available_characters,
    }

    return render(request, 'scenarios/join.html', context)


@login_required
def scenario_archive(request):
    """Show completed scenarios"""
    scenarios = Scenario.objects.filter(
        players__player=request.user,
        status='COMPLETED'
    ).distinct()

    return render(request, 'scenarios/archive.html', {'scenarios': scenarios})