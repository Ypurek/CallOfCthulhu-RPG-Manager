# Template Integration Guide

This guide explains how to integrate the new template components into your existing Cthulhu RPG views.

## Components Created

### 1. Status Effect Badges (_status_effect_badges.html)
**Location**: `templates/characters/_status_effect_badges.html`

**Purpose**: Display character status effects as colored badges

**Integration Points**:
- Character cards in `scenarios/manage.html`
- Player character sheet in `scenarios/detail.html`
- Character profile pages

**Usage Example**:
```django
{% load static %}

{# In character card or sheet #}
<div class="character-info">
    <h3>{{ character.name }}</h3>
    
    {# Include status effect badges #}
    {% with effects=character.status_effects.all %}
        {% include "characters/_status_effect_badges.html" with effects=character.status_effects.all %}
    {% endwith %}
</div>
```

**Backend Requirements**:
- View must provide `effects` or use auto-lookup from `character.status_effects.all`
- This uses the `get_character_status_effects_display()` service function for proper formatting

**Alternative (with service)**: In your view, add:
```python
from scenarios.services import get_character_status_effects_display

# In view function
effects = get_character_status_effects_display(character)

return render(request, template, {
    'character': character,
    'character_effects': effects,
})
```

Then in template:
```django
{% include "characters/_status_effect_badges.html" with effects=character_effects %}
```

---

### 2. Status Effect Modal (_status_effect_modal.html)
**Location**: `templates/scenarios/_status_effect_modal.html`

**Purpose**: Modal dialog for keeper to add status effects to characters

**Integration Points**:
- `scenarios/manage.html` - for each character card (NPC/PC)

**Usage Example**:
```django
{# In scenarios/manage.html character card #}
{% for player_card in player_cards %}
    {{ player_card.sheet.name }}
    
    {# Include status effect modal #}
    {% include "scenarios/_status_effect_modal.html" with character=player_card.sp.character scenario=scenario %}
    
    {# Button to open modal #}
    <button class="btn btn-sm btn-warning" data-bs-toggle="modal" data-bs-target="#statusEffectModal_{{ player_card.sp.character.id }}">
        <i class="bi bi-heart-plus"></i> Add Effect
    </button>
{% endfor %}
```

**Backend Requirements**:
- View must query and pass all StatusEffect objects:
```python
from characters.models import StatusEffect

# In scenario_manage view
all_effects = StatusEffect.objects.all()

return render(request, 'scenarios/manage.html', {
    'scenario': scenario,
    'status_effects': all_effects,
    # ... other context
})
```

**JavaScript Requirements**:
The modal includes JavaScript for handling submissions. Add this to your base template or manage.html:

```html
<script>
document.addEventListener('click', function(e) {
    if (e.target.closest('.add-effect')) {
        handleAddEffect(e.target);
    }
    if (e.target.closest('.add-custom-effect')) {
        handleAddCustomEffect(e.target);
    }
});

function handleAddEffect(button) {
    const characterId = button.dataset.characterId;
    const effectId = button.dataset.effectId;
    const scenarioId = '{{ scenario.id }}'; // Adjust as needed
    
    const formData = new FormData();
    formData.append('effect_id', effectId);
    
    fetch(`/scenarios/${scenarioId}/character/${characterId}/effect/add/`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.ok) {
            alert(`${data.effect_name} added!`);
            location.reload(); // Or update UI dynamically
        }
    });
}

function handleAddCustomEffect(button) {
    const characterId = button.dataset.characterId;
    const scenarioId = button.dataset.scenarioId;
    
    // Get the input values
    const modal = button.closest('#effectCategory_custom');
    const effectName = modal.querySelector('.custom-effect-name').value;
    const duration = modal.querySelector('.custom-effect-duration').value;
    
    if (!effectName) {
        alert('Enter effect name');
        return;
    }
    
    const formData = new FormData();
    formData.append('effect_name', effectName);
    formData.append('remaining_rounds', duration);
    
    fetch(`/scenarios/${scenarioId}/character/${characterId}/effect/add/`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.ok) {
            alert(`Custom effect "${data.effect_name}" added!`);
            location.reload();
        }
    });
}
</script>
```

---

### 3. Messages Display (_messages_display.html)
**Location**: `templates/scenarios/_messages_display.html`

**Purpose**: Display game messages and allow keeper to send messages

**Integration Points**:
- Keeper management page (`scenarios/manage.html`)
- Player detail page (`scenarios/detail.html`) - read-only version

**Usage Example**:
```django
{# In scenarios/manage.html sidebar or tab #}
<div class="messages-section">
    <h5>Communications</h5>
    {% include "scenarios/_messages_display.html" with scenario=scenario is_keeper=True %}
</div>

{# Or for players (read-only) #}
<div class="messages-section">
    {% include "scenarios/_messages_display.html" with scenario=scenario is_keeper=False %}
</div>
```

**Features**:
- Auto-loads and polls messages every 5 seconds for keepers
- Allows keeper to send messages to all players or specific player
- Displays message type (Public/Private) and timestamp
- Auto-scrolls to latest message

**No additional backend requirements** - it uses the existing endpoints:
- `/scenarios/<id>/message/send/` (POST)
- `/scenarios/<id>/messages/` (GET)

---

### 4. Notification Icon (_notification_icon.html)
**Location**: `templates/scenarios/_notification_icon.html`

**Purpose**: Display bell icon with unread message count badge

**Integration Points**:
- Near the scenario day/time display
- In the header of any scenario page

**Usage Example**:
```django
{# In scenarios/detail.html header #}
<div class="scenario-header">
    <h2>{{ scenario.name }}</h2>
    <p>Day {{ scenario.in_game_day }} - {{ scenario.in_game_time|time:"H:i" }}</p>
    
    {# Place notification icon #}
    {% include "scenarios/_notification_icon.html" with scenario=scenario %}
</div>
```

**Features**:
- Shows badge with unread message count
- Pulses when new messages arrive
- Polls for updates every 10 seconds
- Badge shows "99+" if more than 99 unread messages

**No additional backend requirements** - uses:
- `/scenarios/<id>/messages/` (GET)

---

### 5. Skill Update Checkboxes (_skill_update_checkboxes.html)
**Location**: `templates/scenarios/_skill_update_checkboxes.html`

**Purpose**: Keeper-only checkboxes to mark skills needing updates

**Integration Points**:
- Character card in `scenarios/manage.html` (keeper only)
- Appears in skills section of character sheet

**Usage Example**:
```django
{# In scenarios/manage.html character card #}
<div class="character-sheet">
    <h3>{{ character.name }}</h3>
    
    {# Skills section #}
    <div class="skills">
        <!-- Existing skills display -->
        {% for skill in character.skills.all %}
            {{ skill.skill.name }}: {{ skill.value }}%
        {% endfor %}
    </div>
    
    {# Only show checkboxes to keeper #}
    {% include "scenarios/_skill_update_checkboxes.html" with character=character is_keeper=is_keeper %}
</div>
```

**Features**:
- Only visible to keepers
- Highlights checked skills
- Local save functionality
- Shows skills marked for improvement

**Backend Integration** (Optional):
To save skill updates to the database, add this endpoint to `scenarios/views.py`:

```python
@require_POST
@_keeper_required
def scenario_character_mark_skill_for_update(request, scenario_id, character_id):
    """Mark/unmark skills for update after session"""
    scenario = _get_scenario_for_keeper(request, scenario_id)
    character = get_object_or_404(Character, id=character_id)
    
    # Verify character in scenario
    in_scenario = (
        ScenarioPlayer.objects.filter(scenario=scenario, character=character).exists() or
        ScenarioNPC.objects.filter(scenario=scenario, npc=character).exists()
    )
    if not in_scenario:
        return JsonResponse({"ok": False, "error": "Character not in scenario"}, status=403)
    
    # Get skill IDs to mark for update
    skill_ids = request.POST.getlist('skill_ids[]')
    
    # Update all skills: mark selected as needing update
    CharacterSkill.objects.filter(character=character).update(needs_update=False)
    CharacterSkill.objects.filter(
        character=character,
        skill_id__in=skill_ids
    ).update(needs_update=True)
    
    return JsonResponse({"ok": True})
```

And add to `scenarios/urls.py`:
```python
path('<int:scenario_id>/character/<int:character_id>/mark-skills/', 
     views.scenario_character_mark_skill_for_update, 
     name='mark_skills'),
```

Then update the JavaScript in the template to POST to this endpoint.

---

## Integration Checklist

- [ ] Add `{% include "characters/_status_effect_badges.html" %}` to character cards
- [ ] Add `{% include "scenarios/_status_effect_modal.html" %}` to manage.html
- [ ] Add `{% include "scenarios/_messages_display.html" %}` to keeper/player pages
- [ ] Add `{% include "scenarios/_notification_icon.html" %}` to scenario header
- [ ] Add `{% include "scenarios/_skill_update_checkboxes.html" %}` to character cards (keeper only)
- [ ] Update views to pass `status_effects`, `is_keeper` context variables
- [ ] Add JavaScript handlers for status effect modal buttons
- [ ] Test all endpoints with Django management shell

## Testing

```bash
# Test endpoints
python manage.py shell
>>> from scenarios.models import Scenario
>>> from characters.models import StatusEffect
>>> scenario = Scenario.objects.first()
>>> effects = StatusEffect.objects.all()
>>> effects.count()  # Should show seed effects
```

Test in browser by:
1. Opening keeper management page
2. Verifying status effect modal opens
3. Checking notification icon updates
4. Sending test message and verifying it appears
5. Verifying skill checkboxes appear only to keeper

## Performance Considerations

- Polling happens every 5-10 seconds - adjust intervals in JavaScript for different use cases
- Status effects query uses `select_related` and `prefetch_related` for optimization
- Consider caching status effects list if it grows large
- Add database indexes on foreign keys if not already present

## Future Enhancements

- WebSocket support for real-time updates instead of polling
- Sound notifications for new messages
- Message history pagination
- Archiving old messages
- Status effect timeline view
- Bulk skill update operations
