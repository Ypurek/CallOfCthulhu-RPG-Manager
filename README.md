# Call of Cthulhu RPG Management System

Web app for running Call of Cthulhu sessions with role-based flows for Players and Keepers.

## What Is Implemented

- Role-based auth (`PLAYER`, `KEEPER`) with custom user model.
- Character management:
  - character list/detail/edit/delete
  - multi-step create and edit wizards
  - template-based creation (PC and NPC templates)
  - JSON import/export for create/edit flows
  - cemetery for dead characters
- Scenario/session management:
  - create/edit/delete scenarios
  - player invitations and join flow
  - keeper manage page for cast/NPC/session controls
  - in-game time controls with HP/MP recovery logic
  - public and keeper notes
  - private player session notes
- Encounter tools:
  - fight mode start/end
  - participant add/remove
  - initiative ordering with prepared-weapon DEX bonus
  - round controls
- Session messaging:
  - keeper-to-player private messages
  - unread tracking and player popup modal
- Status effects management in session.
- Hint system:
  - admin CRUD for hints (`PLAYER` / `KEEPER` audience)
  - player hints popup carousel
  - dedicated keeper hints page
- Test coverage for core, characters, and scenarios apps.

For a requirements-level breakdown, see `docs/requirements.md`.

## Tech Stack

- Python `>=3.13` (project config)
- Django `>=5.3`
- SQLite (default DB)
- HTML/CSS/JavaScript templates (server-rendered)

## Project Structure

- `core/` - auth, dashboard, base user functionality
- `characters/` - character models, wizards, templates, import/export
- `scenarios/` - scenario sessions, fight mode, messaging, hints
- `templates/` - UI templates
- `docs/` - project docs and requirements

## Quick Start

### 1) Install dependencies

Using `uv` (recommended):

```powershell
uv sync
```

Or with pip:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

### 2) Apply migrations

```powershell
python manage.py migrate
```

### 3) Create admin user (optional but recommended)

```powershell
python manage.py createsuperuser
```

### 4) Run the server

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Running Tests

Run all tests:

```powershell
python manage.py test
```

Run app-specific tests:

```powershell
python manage.py test core
python manage.py test characters
python manage.py test scenarios
```

## Internationalization

- Active languages in settings: Ukrainian (`uk`) and English (`en`)
- Locale files are under `locale/`
- A helper script exists: `compile_mo.py`

## Documentation

- Requirements and traceability: `docs/requirements.md`

## Current Scope Notes

This repository contains implemented gameplay/session management features and tests. Some product ideas from earlier planning docs are not fully implemented yet (for example, rich text editor in notes with image upload, or broader language set beyond current settings).

## License

No license yet