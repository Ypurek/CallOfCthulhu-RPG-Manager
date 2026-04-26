from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
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

    # Get character skills
    character_skills = CharacterSkill.objects.filter(character=character).select_related('skill')

    # Separate skills by category
    skills_by_category = {
        'mutual': [],
        'general': [],
        'combat': [],
        'language': []
    }

    for char_skill in character_skills:
        category = char_skill.skill.category
        skills_by_category[category].append(char_skill)

    # Sort each category by skill value (descending)
    for category in skills_by_category:
        skills_by_category[category].sort(key=lambda x: x.value, reverse=True)

    # Calculate success levels for popup
    def get_success_levels(value):
        return {
            'regular': value,
            'hard': value // 2,
            'extreme': value // 5
        }

    context = {
        'character': character,
        'skills_by_category': skills_by_category,
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