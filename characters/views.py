from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Character, CharacterSkill, Skill


@login_required
def character_list(request):
    """List user's alive characters"""
    characters = Character.objects.filter(
        owner=request.user,
        is_alive=True,
        character_type='PC'
    )
    return render(request, 'characters/list.html', {'characters': characters})


@login_required
def character_detail(request, character_id):
    """Display character sheet"""
    character = get_object_or_404(
        Character,
        id=character_id,
        owner=request.user
    )

    if request.method == 'POST':
        character.player_notes = request.POST.get('player_notes', '').strip()
        character.save(update_fields=['player_notes', 'updated_at'])
        messages.success(request, 'Notes saved.')
        return redirect('characters:detail', character_id=character.id)

    character_skills = CharacterSkill.objects.filter(character=character).select_related('skill')
    character_skills_by_skill_id = {char_skill.skill_id: char_skill for char_skill in character_skills}

    def serialize_skill(skill):
        char_skill = character_skills_by_skill_id.get(skill.id)
        value = char_skill.value if char_skill else skill.base_value
        # Native language is always derived from EDU on the character sheet.
        if skill.name in {'Own Language', 'English'}:
            value = character.education
        return {
            'id': skill.id,
            'name': skill.name,
            'description': skill.description,
            'value': value,
            'base_value': skill.base_value,
            'is_default': value == skill.base_value,
        }

    non_combat_skills = [
        serialize_skill(skill)
        for skill in Skill.objects.exclude(category='combat').order_by('name')
    ]
    non_combat_skills.sort(key=lambda skill: (-skill['value'], skill['name']))

    combat_skills = [
        serialize_skill(skill)
        for skill in Skill.objects.filter(category='combat').order_by('name')
    ]
    combat_skills.sort(key=lambda skill: (-skill['value'], skill['name']))

    visible_non_combat_skills = [skill for skill in non_combat_skills if not skill['is_default']]
    default_non_combat_skills = [skill for skill in non_combat_skills if skill['is_default']]
    default_non_combat_skills.sort(key=lambda skill: skill['name'].lower())

    def get_success_levels(value):
        return {
            'regular': value,
            'hard': value // 2,
            'extreme': value // 5
        }

    context = {
        'character': character,
        'skills': visible_non_combat_skills,
        'default_skills': default_non_combat_skills,
        'combat_skills': combat_skills,
        'dodge_value': character.dexterity // 2,
        'can_add_custom_skill': request.user.is_keeper() or request.GET.get('creation') == '1',
        'get_success_levels': get_success_levels,
    }

    return render(request, 'characters/detail.html', context)


@login_required
def character_edit(request, character_id):
    """Edit character (for keepers during game)"""
    character = get_object_or_404(Character, id=character_id)

    # Check if user can edit this character
    # (either owner or keeper of current scenario)
    can_edit = (
        character.owner == request.user or
        request.user.is_keeper()
    )

    if not can_edit:
        messages.error(request, "You don't have permission to edit this character.")
        return redirect('characters:detail', character_id=character_id)

    if request.method == 'POST':
        # Handle AJAX requests for stat updates
        if request.headers.get('Content-Type') == 'application/json':
            import json
            data = json.loads(request.body)

            stat = data.get('stat')
            value = data.get('value')

            if stat and value is not None:
                if hasattr(character, stat):
                    setattr(character, stat, value)
                    character.save()
                    return JsonResponse({'success': True})

        return JsonResponse({'success': False})

    return render(request, 'characters/edit.html', {'character': character})


@login_required
def character_create(request):
    """Create new character"""
    # TODO: Implement character creation form
    return render(request, 'characters/create.html')


@login_required
def character_templates(request):
    """Character templates page"""
    # TODO: Implement character templates
    return render(request, 'characters/templates.html')


@login_required
def character_cemetery(request):
    """Show user's dead characters"""
    dead_characters = Character.objects.filter(
        owner=request.user,
        is_alive=False,
        character_type='PC'
    )
    return render(request, 'characters/cemetery.html', {'characters': dead_characters})