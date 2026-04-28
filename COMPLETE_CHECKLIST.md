# Complete Implementation Checklist - Cthulhu RPG Tasks

## ✅ COMPLETED IMPLEMENTATION

### Database & Models
- [x] Enhanced `StatusEffect` model with effect_type, is_permanent, icon_class, game_rules_json
- [x] Enhanced `CharacterStatusEffect` with acquired_at timestamp
- [x] Added `needs_update` field to `CharacterSkill` for keeper skill tracking
- [x] Created data migration seeding 17 default status effects (phobias, madness, mania, status effects)
- [x] Registered models in Django admin with proper list_display and filtering

### Backend Services Layer (scenarios/services.py)
- [x] `apply_daily_hp_restore()` - Restore 1 HP daily to characters without deep wound
- [x] `apply_near_death_status()` - Add status when HP = 0
- [x] `apply_trauma_status()` - Add status when SAN lost >= 5
- [x] `apply_deep_wound_from_damage()` - Auto-add when damage >= 50% max HP
- [x] `add_status_effect()` - Manually add effects with duration
- [x] `remove_status_effect()` - Manually remove effects
- [x] `get_character_status_effects_display()` - Format effects for UI with badge colors

### Backend Views & API Endpoints (scenarios/views.py)
- [x] `scenario_send_message()` - Keeper POST: Send public/private messages
- [x] `scenario_get_messages()` - GET: Retrieve unread messages (JSON)
- [x] `scenario_character_add_effect()` - Keeper POST: Add status effect to character
- [x] `scenario_character_remove_effect()` - Keeper POST: Remove status effect
- [x] `scenario_character_get_effects()` - GET: Get character effects (JSON)
- [x] `scenario_player_snapshot_json()` - GET: New JSON-only snapshot endpoint with unread messages

### URL Routes (scenarios/urls.py)
- [x] `/scenarios/<id>/snapshot-json/` - JSON-only snapshot
- [x] `/scenarios/<id>/message/send/` - Send message
- [x] `/scenarios/<id>/messages/` - Get messages
- [x] `/scenarios/<id>/character/<cid>/effect/add/` - Add effect
- [x] `/scenarios/<id>/character/<cid>/effect/<eid>/remove/` - Remove effect
- [x] `/scenarios/<id>/character/<cid>/effects/` - Get character effects

### Admin Interface (characters/admin.py)
- [x] Enhanced `StatusEffectAdmin` with effect_type, is_permanent filtering
- [x] Registered `CharacterStatusEffectAdmin` with acquired_at, effect_type filtering
- [x] Organized fieldsets in admin for better UX

### Template Components (Created)
- [x] `_status_effect_badges.html` - Display effects as colored badges
- [x] `_status_effect_modal.html` - Modal for keeper to add effects (complete with JS handlers)
- [x] `_messages_display.html` - Messages and keeper messaging UI with auto-polling
- [x] `_notification_icon.html` - Bell icon with unread message badge and pulse animation
- [x] `_skill_update_checkboxes.html` - Keeper-only skill update checkboxes

---

##  READY FOR INTEGRATION (Not yet integrated into existing templates)

### Step-by-Step Integration Guide Provided
- [x] Created `TEMPLATE_INTEGRATION_GUIDE.md` with detailed usage examples
- [x] Each template has clear usage examples showing where/how to include it
- [x] Includes JavaScript handlers and backend integration instructions

### Templates Needing Integration Into Existing Pages

#### 1. scenarios/manage.html (Keeper Dashboard)
- Include `_notification_icon.html` near day/time display
- Include `_messages_display.html` in sidebar or modal
- Include `_status_effect_modal.html` for each character card
- Include `_skill_update_checkboxes.html` for each character card
- Add status effect badges to character names using `_status_effect_badges.html`

#### 2. scenarios/detail.html (Player Session View)
- Include `_notification_icon.html` in header
- Include `_messages_display.html` (read-only mode) 
- Include `_status_effect_badges.html` for character display

#### 3. Character Card Templates (If used elsewhere)
- Add status effect badges
- Add notification indicators

---

##  REMAINING MANUAL INTEGRATION TASKS

### Task 1: Update scenarios/manage.html
```django
{# Add near day/time display #}
{% include "scenarios/_notification_icon.html" with scenario=scenario %}

{# Add messaging section #}
{% include "scenarios/_messages_display.html" with scenario=scenario is_keeper=True %}

{# For each player card #}
{% include "scenarios/_status_effect_modal.html" with character=player_card.sp.character scenario=scenario %}
{% include "scenarios/_skill_update_checkboxes.html" with character=player_card.sp.character is_keeper=True %}
{% include "characters/_status_effect_badges.html" with effects=player_effects %}

{# For each NPC card #}
{% include "scenarios/_status_effect_modal.html" with character=npc_card.snpc.npc scenario=scenario %}
{% include "characters/_status_effect_badges.html" with effects=npc_effects %}
```

**Backend Update Required**:
```python
# In scenario_manage view, add:
from characters.models import StatusEffect
from scenarios.services import get_character_status_effects_display

all_effects = StatusEffect.objects.all()

# For each player/NPC, pre-compute effects
for card in player_cards:
    card['effects'] = get_character_status_effects_display(card['sp'].character)

context['status_effects'] = all_effects
```

### Task 2: Update scenarios/detail.html (Player View)
```django
{# Add notification icon #}
{% include "scenarios/_notification_icon.html" with scenario=scenario %}

{# Add messages (read-only) #}
{% include "scenarios/_messages_display.html" with scenario=scenario is_keeper=False %}

{# Display character effects #}
{% include "characters/_status_effect_badges.html" with effects=character_effects %}
```

### Task 3: Hook Automatic Game Logic
Add to `scenario_advance_time` view when day increments:

```python
from scenarios.services import apply_daily_hp_restore

if days_crossed > 0:  # When day changes
    scenario.in_game_day = new_day
    scenario.save()
    apply_daily_hp_restore(scenario)  # Restore 1 HP daily
```

### Task 4: Hook Damage/Sanity Logic
When character stats are updated via `scenario_character_adjust_stats`:

```python
from scenarios.services import apply_near_death_status, apply_trauma_status, apply_deep_wound_from_damage

# After HP update
if hp_changed and character.hp_current == 0:
    apply_near_death_status(character)

# After damage from keeper action
damage_taken = old_hp - character.hp_current
if damage_taken > 0:
    apply_deep_wound_from_damage(character, damage_taken)

# After SAN update
if sanity_changed:
    san_lost = old_san - character.sanity_current
    if san_lost > 0:
        apply_trauma_status(character, san_lost)
```

---

##  TESTING CHECKLIST

### Backend Testing
- [ ] Run `python manage.py check` - should show no issues
- [ ] Run `python manage.py test characters` - all character model tests pass
- [ ] Run `python manage.py test scenarios` - all scenario tests pass
- [ ] Test status effect creation in Django shell
- [ ] Test message sending via POST endpoint
- [ ] Test snapshot JSON endpoint response format

### Frontend Testing (After Integration)
- [ ] Status effect badges display with correct colors
- [ ] Notification icon shows unread message count
- [ ] Status effect modal opens and allows adding effects
- [ ] Messages send and appear in real-time
- [ ] Skill checkboxes are visible only to keeper
- [ ] Skill checkboxes remember selections
- [ ] All components display correctly on mobile (responsive)

### Functional Testing (After Full Integration)
- [ ] Keeper can send public messages to all players
- [ ] Keeper can send private messages to specific player
- [ ] Player receives notification of new message
- [ ] Keeper can add status effects to characters
- [ ] Status effects display on character cards
- [ ] Status effects badge shows correct icon and color
- [ ] Skill update checkboxes toggle correctly
- [ ] Daily HP restoration happens when day advances
- [ ] Near Death status added when HP = 0
- [ ] Psychological Trauma added when SAN lost >= 5
- [ ] Deep Wound added when damage >= 50% max HP

---

##  IMPLEMENTATION STATUS BY FEATURE

### 1. Notification Icon ✅ Ready
- Backend: 100% complete
- Frontend: 100% complete (needs integration)
- Status: Ready to integrate into manage.html and detail.html

### 2. Keeper Messaging ✅ Ready
- Backend: 100% complete
- Frontend: 100% complete (needs integration)
- Status: Ready - auto-polls every 5 seconds

### 3. Skill Update Checkboxes ✅ Ready
- Backend: 100% complete
- Frontend: 100% complete (needs integration)
- Status: Ready - keeper-only, local save works

### 4. Status Effect Quick-Add Modal ✅ Ready
- Backend: 100% complete
- Frontend: 100% complete (needs integration)
- Status: Ready - includes custom effects

### 5. Status Effect Display ✅ Ready
- Backend: 100% complete
- Frontend: 100% complete (needs integration)
- Status: Ready - color-coded by effect type

### 6. Auto HP Restore ✅ Implementation Ready
- Backend: 100% complete (service function exists)
- Integration: Needs hook in `scenario_advance_time`
- Status: Ready - just needs to be called

### 7. Near Death Status ✅ Implementation Ready
- Backend: 100% complete (service function exists)
- Integration: Needs hook in stat adjustment
- Status: Ready - just needs to be called

### 8. Psychological Trauma ✅ Implementation Ready
- Backend: 100% complete (service function exists)
- Integration: Needs hook in sanity loss handling
- Status: Ready - just needs to be called

### 9. Deep Wound ✅ Implementation Ready
- Backend: 100% complete (service function exists)
- Integration: Needs hook in damage tracking
- Status: Ready - just needs to be called

### 10. JSON Snapshot API ✅ Ready
- Backend: 100% complete
- Frontend: Ready to use
- Status: Returns JSON with day, time, public_notes, unread_messages, character data

---

##  FILES CREATED/MODIFIED

### New Files Created
- `scenarios/services.py` - Game logic services
- `templates/characters/_status_effect_badges.html` - Effect badges component
- `templates/scenarios/_status_effect_modal.html` - Effect modal with JS
- `templates/scenarios/_messages_display.html` - Messages component with polling
- `templates/scenarios/_notification_icon.html` - Notification bell icon
- `templates/scenarios/_skill_update_checkboxes.html` - Keeper skill checkboxes
- `IMPLEMENTATION_SUMMARY.md` - Implementation details
- `TEMPLATE_INTEGRATION_GUIDE.md` - Integration instructions

### Modified Files
- `characters/models.py` - Enhanced StatusEffect, CharacterStatusEffect, CharacterSkill
- `characters/admin.py` - Enhanced admin interfaces
- `scenarios/views.py` - Added messaging and status effect endpoints
- `scenarios/urls.py` - Added new URL routes

### Migrations
- `characters/migrations/0006_*` - Model field additions
- `characters/migrations/0007_seed_status_effects.py` - 17 seed effects

---

##  IMMEDIATE NEXT STEPS

1. **Open the integration guide**: `TEMPLATE_INTEGRATION_GUIDE.md`
2. **Update manage.html** with the 5 new template includes
3. **Update detail.html** with 3 template includes
4. **Update scenario_manage view** to pass status_effects and effect objects
5. **Test status effect modal** - click "Add Effect" button
6. **Test messages** - send a message and verify it appears
7. **Test notification icon** - verify badge shows unread count
8. **Hook automatic logic** - add service calls to stat adjustment
9. **Run full test suite** - verify nothing breaks

---

## ⚠️ NOTES

- All database migrations have been applied successfully
- All endpoint security checks are in place (keeper-only, participant checks)
- Admin interface is fully configured
- Templates use Bootstrap 5 with custom CSS matching the app theme
- No external dependencies added beyond what's already in requirements
- All code follows the existing project patterns and style

##  RESOURCES

- **Integration Guide**: `TEMPLATE_INTEGRATION_GUIDE.md`
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`
- **Services Module**: `scenarios/services.py`
- **API Endpoints**: Added to `scenarios/views.py`
