# Project Requirements (Implemented Scope)

This document captures the current requirements based on:

- implemented code in `core/`, `characters/`, `scenarios/`
- route definitions in `core/urls.py`, `characters/urls.py`, `scenarios/urls.py`
- behavior validated by `core/tests.py`, `characters/tests.py`, `scenarios/tests.py`
- the original product intent from the previous README draft

Status legend:

- `Implemented` - available in code and test-covered
- `Partial` - available in limited form
- `Planned` - described in product intent but not currently implemented

## 1. User and Access Requirements

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| AUTH-01 | Users can register and authenticate | Implemented | `core/urls.py`, `core/tests.py::AuthViewsTest` |
| AUTH-02 | Default role is Player | Implemented | `core/tests.py::UserModelTest.test_default_role_is_player` |
| AUTH-03 | Keeper role has elevated scenario controls | Implemented | keeper checks in `scenarios/views.py`, permission tests in `scenarios/tests.py::PermissionTests` |
| AUTH-04 | Admin/staff can access cross-scenario keeper actions | Implemented | `scenarios/tests.py::PermissionTests.test_admin_can_manage_any_scenario` |

## 2. Character Requirements

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| CHAR-01 | Create characters with multi-step wizard | Implemented | `characters/urls.py` (`create`), `characters/tests.py::CharacterCreateWizardTests` |
| CHAR-02 | Edit existing characters with wizard | Implemented | `characters/urls.py` (`edit_wizard`), `characters/tests.py::CharacterEditWizardStateTransitionTests` |
| CHAR-03 | Character templates (create/edit/delete/use) | Implemented | template routes in `characters/urls.py`, template tests in `characters/tests.py` |
| CHAR-04 | NPC templates and NPC wizard flows | Implemented | NPC template routes in `characters/urls.py`, tests in `characters/tests.py::NPCTemplateViewTests` |
| CHAR-05 | Character import/export JSON | Implemented | `create_import_json`, `create_export_json`, tests in `characters/tests.py::CharacterImportExportTests` |
| CHAR-06 | Character list/detail/delete/cemetery | Implemented | `characters/urls.py`, view tests in `characters/tests.py` |
| CHAR-07 | Character model derives HP/MP/build/damage bonus | Implemented | model tests in `characters/tests.py` |

## 3. Scenario and Session Requirements

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| SCN-01 | Keeper can create/edit/delete scenarios | Implemented | `scenarios/urls.py`, CRUD tests in `scenarios/tests.py` |
| SCN-02 | Scenario invitations and join flow | Implemented | invitation/join routes, tests in `scenarios/tests.py::InvitationTests` |
| SCN-03 | Session manage page for cast and NPC control | Implemented | `scenarios/views.py::scenario_manage`, tests in `scenarios/tests.py::ScenarioManageTest` |
| SCN-04 | Player session detail view with own character | Implemented | `scenarios/views.py::scenario_detail`, tests in `scenarios/tests.py::ScenarioDetailTest` |
| SCN-05 | Public and keeper notes in scenario | Implemented | `scenario_save_notes`, tests in `scenarios/tests.py::ScenarioNotesTest` |
| SCN-06 | Private player session notes | Implemented | `scenario_player_save_private_notes`, tests in `scenarios/tests.py::ScenarioDetailTest.test_player_can_save_private_session_notes` |
| SCN-07 | In-game time update with recovery side effects | Implemented | `scenario_advance_time`, `scenario_set_time`, tests in `scenarios/tests.py::ScenarioTimeTest` |
| SCN-08 | Remove player or unassign player character in scenario | Implemented | `scenario_player_remove`, `scenario_player_unassign_character` |

## 4. Fight and Encounter Requirements

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| FIGHT-01 | Start/end fight encounter | Implemented | `fight_start`, `fight_end`, tests in `scenarios/tests.py::ScenarioFightModeTest` |
| FIGHT-02 | Add/remove participants from scenario cast | Implemented | `fight_add_participant`, `fight_remove_participant`, tests in `ScenarioFightModeTest` |
| FIGHT-03 | Initiative ordering by DEX, prepared weapon modifies DEX | Implemented | `scenarios/views.py::_fight_effective_dex`, tests in `ScenarioFightModeTest.test_prepared_weapon_doubles_dex_and_resorts` |
| FIGHT-04 | Round controls | Implemented | `fight_advance_turn`, `fight_reset_turns`, tests in `ScenarioFightModeTest` |
| FIGHT-05 | Explicit current-turn pointer in UI | Partial | model has `current_turn_index`; current UI emphasizes round/order but not a dedicated turn pointer element |

## 5. Messaging and Effects Requirements

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| MSG-01 | Keeper can send private messages to scenario players | Implemented | `scenario_send_message`, tests in `scenarios/tests.py::ScenarioMessagingTest` |
| MSG-02 | Player sees unread count and can mark messages read | Implemented | `scenario_get_messages`, `scenario_mark_messages_read`, tests in `ScenarioMessagingTest` |
| MSG-03 | Player receives modal/popup notifications in session page | Implemented | client logic in `templates/scenarios/detail.html` and related tests |
| FX-01 | Keeper can add/remove status effects during session | Implemented | `scenario_character_add_effect`, `scenario_character_remove_effect`, tests in `ScenarioStatusEffectsTest` |

## 6. Hints Requirements

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| HINT-01 | Separate hints by audience (Player/Keeper) | Implemented | `scenarios/models.py::Hint` |
| HINT-02 | Admin CRUD for hints | Implemented | `scenarios/admin.py::HintAdmin` |
| HINT-03 | Player hints available as popup cards/carousel | Implemented | `templates/scenarios/detail.html` (`playerHintsModal`) |
| HINT-04 | Keeper hints available on dedicated page | Implemented | `scenarios/views.py::scenario_keeper_hints`, `templates/scenarios/keeper_hints.html`, tests in `ScenarioKeeperHintsViewTest` |

## 7. Non-Functional Requirements

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| NFR-01 | Server-rendered web app using Django | Implemented | project structure and settings |
| NFR-02 | SQLite as default DB | Implemented | `cthulhu_rpg/settings.py` |
| NFR-03 | Mobile-friendly player sheet UI | Implemented | template structure and CSS in character/scenario templates |
| NFR-04 | Automated tests for major flows | Implemented | `core/tests.py`, `characters/tests.py`, `scenarios/tests.py` |
| NFR-05 | Multi-language support baseline | Partial | configured languages: `uk`, `en` (`settings.py`); broader language set from old vision is not implemented |

## 8. Gaps vs Original Product Intent

The following are intentionally tracked as not fully implemented in current code:

- Rich text editor for notes with formatting and image upload (`Planned`)
- Additional language pack(s) beyond currently configured `uk` and `en` (`Planned`)
- Broader world-building/template management outside currently implemented NPC/character flows (`Planned`)

## 9. Acceptance Baseline for Current Release

A release can be considered aligned with current implemented requirements when:

1. Core auth flows pass (`core` tests).
2. Character wizard/template/import-export flows pass (`characters` tests).
3. Scenario manage, invitations, time progression, fight, messaging, effects, and hints flows pass (`scenarios` tests).
4. Keeper and player UI paths are reachable from route entry points without permission leaks.

