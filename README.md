# Call of Cthulhu RPG Management System

and Keepers (game masters).
The system allows users to create and manage characters, scenarios, and game sessions.

## Idea

The paper character sheets are too big, because must keep all the possible skills and items. In real game sessions,
only a subset of these skills and items are used. The idea is that players have only important skills and stats, visible
on a single phone screen, sorted by level. Keeper can update the character sheets during and after the session, so
players
are not distracted with unimportant details. Players just roll the dices, having fun and getting more immersive
experience.

## Description

The web application will have the following features:

- User authentication and role management (Player, Keeper)
- Superuser (Django superuser) can manage users and roles, have access to Django admin panel. It is built-in Django
  functionality.

## User

After the registration, every user has the Player role by default.  
After the authentication, the user is redirected to the dashboard, where they can see

- their alive characters list
- ongoing scenarios they are participating in
  User can navigate to the following pages:
- archive of past scenarios
- character templates (to create new characters from predefined templates)
- character builder (to create new characters from scratch, using Call of Cthulhu rules)
- cemetery of own dead characters

User can join the ongoing sessions by accepting invitations from Keepers - follow by the invite URL link.  
Joining the session, user should select one of their alive characters, not currently in an active game session.  
When user opens the game session page, they can see:

1. name of the scenario,
2. in-game time
3. their character sheet
4. notes section, where they can write their own notes

In case the Keeper updates the character sheet during the game session, user receives a notification and can see the
changes.  
In case the character dies during the session, user receives a notification and can be navigated to select another alive
character for the session.

## Keeper

Keeper can do everything what Player can do, plus the following:

- create and manage own game sessions
- invite players to join the game sessions
- remove all Players in own game sessions
- participate in sessions of other Keepers as a Player
- manage all characters of own game sessions
    - remove characters from the game session
    - edit character sheets during the game session (stats, skills, items)
    - mark characters` skills improvements to be updated after the session
    - mark that character has prepared the weapon (this should add +50 to the Dexterity)
- manage all NPCs in own game sessions
- do a public notes, visible to all players in the game session
- do a private notes, visible only to the Keeper
- update in-game time
- end the game session
- start the fight mode
- manage (create, edit, delete)
    - NPC templates,
    - weapon templates
    - spell templates
    - list of mental disorders

## Fight encounter

Keeper is navigated to the fight encounter page as the Keeper starts the fight mode.
Keeper can add NPCs to the encounter from the NPC, already added to the sessions and Players` characters. Additionally,
Keeper can add any other NCP from the NPC templates.
The encounter page must display to the Keeper

- the list of all Characters and NPCs in the encounter, sorted by their Dexterity.
- pointer to the current character/NPC turn
- Round number
- collapsible character/NPC sheets, displaying important stats (HP, SAN, etc.) with ability to expand the full sheet and
  edit it, add status effects and notes
- buttons to move to the next turn, end the fight mode
- send notifications to Players with private messages
- Players can receive popup notifications when Keeper sends them private messages. It should appear as a popup on the
  Player’s screen, with the message and the name of the sender (Keeper). The message should be stored in the database
  and visible in the character sheet of the Player, so they can refer to it
  In case character or NPC dies, Keeper can mark it as dead, so it is removed from the turn order.
  In case the fight mode ends, Keeper is navigated back to the main game session page.

## Design technical decisions and limitations

- The system is implemented as a web application using Django framework for the backend.
- The system is developed using python 3.14 and uv
- The frontend is built using HTML, CSS, and JavaScript, with optional use of frontend frameworks like React or Vue.js
  for enhanced user experience.
- The database used is SQLite.
- The application is designed to be responsive and mobile-friendly, allowing users to access it from various devices.
    - it is planned Players will mostly use mobile phones during the game sessions
    - Keepers may use tablets or laptops for better management capabilities
- the system should be multilingual (English, Spanish, Ukrainian). English language is the default one, and only it
  should be implemented in the first version. The other languages can be added later, using Django’s built-in
  internationalization framework.

## Character sheet

The character sheet, visible to the player on the single screen should contain:

- name
- short description about the character with advise how to play. If the character lacks the combat skills, the
  description should advise to avoid combat and focus on investigation and roleplay. If the character has high combat
  skills, the description should advise to be more aggressive and take the lead in combat situations.
- life points (as a red bar and a number, 10/12 HP). Max life points are calculated as (STR + CON) / 10 rounded down.
- sanity points (as a green bar and a number, 20/30 SAN). Also, maximum level of sanity is calculated as 99 - Cthulhu
  Mythos (one of skills).
- mana points (as a blue bar and a number, 5/10 MP). Max mana points are calculated as POW / 5 rounded down.
- luck points (as a yellow bar and a number, 55/100 LCK)
- list of main stats (Strength, Constitution, Dexterity, Intelligence, Power, Size, Appearance, Education) as a single
  number (in range 0 - 100). On tap on the number the popup should be displayed with success points (regular / high /
  extreme) and a sort description what the stat stands for.
- cash. Start cash is calculated from the Credit Rating (one of skills).
    - 0% - 0$ cash
    - 1-9% - x * 1
    - 10-49% - x * 2
    - 50-89% - x * 5
    - 90-100% - x * 20
- Also build must not be displayed within main stats in regular play, but should be displayed during the combat. It is
  derived as sum(strength + size).
    - If the sum is less than 65, the build is -2,
    - if the sum is between 65 and 84, the build is -1,
    - if the sum is between 85 and 124, the build is 0,
    - if the sum is between 125 and 164, the build is 1,
    - if the sum is between 165 and 204, the build is 2
- List of status effects, with the name of the effect and the remaining rounds
- List of non-combat skills, sorted by level, with the most important skills on top. Each skill should have a name and a
  level (in range 0 - 100). On tap on the skill, the popup should be displayed with success points (regular / high /
  extreme) and
  a sort description what the skill stands for. Every character should have all possible skills with their default
  values, but if skil is default, it should be hidden by default. User can expand the list of skills to see them all.
- Also, the Keeper should have a possibility to mark any skill, even the default one, to be improved after the session.
  It should be displayed as a checkbox near the skill. When the keeper marks it, it should be
  stored in the database and visible in the character sheet of the player, so they can refer to it after the session
  and update their character sheet accordingly.
    - also the native language skill (english) must be always visible, and it's level must be equal to EDU
- list of combat skills, collapsed by default, as the same list as the list above, but with a weapon icon (like
  shooting, melee, etc). Here
  also must be the dodge skill, wich is calculated as a half of the Dexterity. On tap on the combat skill, the popup
  should be displayed with success points (regular / high / extreme) and a sort description what the skill stands for.
- in compat skills there must be a compact notification, that a prepared weapon will increase the Dexterity by 50
  points, so it is important to keep it in mind during the combat. On tap on the notification, the popup should be
  displayed with the description of the prepared weapon and its stats.
- In the compat skills section also must be the list of weapons possessed by the character, with the weapon name and the
  damage (in format like 1D6 + BD (bonus damage), as example). On tap on, the popup should be displayed with the weapon
  stats and description.
    - bonus damage is calculated from the build.
        - if the build is -2, the bonus damage is -2
        - if the build is -1, the bonus damage is -1
        - if the build is 0, the bonus damage is 0
        - if the build is 1, the bonus damage is 1D4
        - if the build is 2, the bonus damage is 1D6
- Compact list of items, possessed by the character with their quantity.
- List of known spells

### More character details

- List of skills must be divided into collapsible-expandable sections.
- The character info can be imported and exported as a JSON file.
- Also, the page, displayed to the player as well as a character sheet, should display in-game time and notes section
- Keeper should have possibility easily modify any character data during the game session, update life, sanity etc
  with +- buttons, update main stats and skill levels, mark skills to be updated, add and remove items and weapons and
  items.

## Scenario management page (Keeper)

This page should display:

- name of the scenario
- in-game time and buttons +30 min, +1 hour, +2 hours, +5 hours
- list of players in the session with ability to invite and remove
- list of characters with ability to add and remove
- list of NPCs. On tap on the NPC, the popup should be displayed with the NPC stats and description
- notes section, with two tabs - public and private. Public notes are visible to all players in the session, private
  notes are visible only to the Keeper. Both sections should have a text editor with ability to format text (bold,
  italic,
  underline, bullet points, etc) and add images (like maps, pictures of NPCs, etc). The notes should be stored in the
  database and
  visible for players when they open the session page. Players can also receive notifications when Keeper updates the
  public notes, so they can refer to it during the game session.

- The keeper can edit the character stats during the game session
- The keeper can mark the character's skills improvements to be updated after the session. It should be displayed as a
  checkbox near the skill. When the keeper marks it, it should be stored in the database and visible in the character
  sheet of the player, so they can refer to it after the session and update their character sheet accordingly.

## NPC management page (Keeper)

On this page should be a wizard to create and edit NPCs. The NPC should have the same stats as the character sheet, but
without the need to create a character sheet for it. The NPC should have a name, description, stats, skills, items and
spells. The NPC should be stored in the database and visible in the NPC list of the scenario management page. The keeper
can add the NPC to the fight encounter, so it is visible for players during the fight mode.

## Character templates page

This page should display a list of character templates, with the name and description of the template. On tap on the
template, the popup should be displayed with the template stats and description. The player can create a character from
the template, by clicking on the "Create character" button. The character should be created with the stats and
description from the template, but the player can edit it after the creation. The character should be stored in the
database and visible in the character list of the player. The player can also create a character from scratch, by
clicking on the "Create character from scratch" button. The character should be created with default stats and
description, but the player can edit it after the creation. The character should be stored in the database and visible
in the character list of the player.

## Page Design

### Character sheet
Character sheet should fit on a single screen of a mobile phone, with the following layout:
- description is collapsible
- status effects are displayed as a list of badges with the name of the effect and the remaining rounds. Visible only if
  there are any status effects.
- stats are displayed in 1 row with the name of the stat and its value. On tap on the stat, the popup should be
  displayed with success points (regular / high / extreme) and a sort description what the stat stands for.
- All non-compat skills first, sorted by level. Skills of the default level are not displayed but there is a button to
  expand/hide the list
- Cthulhu Mythos, credit rating and jump skills are always displayed, even if it is default
- Combat skills are displayed in a separate section, collapsed by default, with a weapon icon. Here also must be the
  dodge skill, which is calculated as a half of the Dexterity. On tap on the combat skill, the popup should be displayed
  with success points (regular / high / extreme) and a sort description what the skill stands for.
- Within combat skills there must be a compact notification, that a prepared weapon will increase the Dexterity by 50
  points, so it is important to keep it in mind during the combat. On tap on the notification, the popup should be
  displayed with the description of the prepared weapon and its stats.
- Within the compat skills the list of weapons possessed by the character, with the weapon name and the damage, number
  of rounds
- items are displayed in a compact form, with the name of the item and its quantity
- spells are displayed in a compact form, with the name of the spell and its mana cost
- notes section is displayed as a text area, where the player can write their own notes. The notes should be stored in
  the
  database and visible for the player when they open the character sheet.
- also if the keeper sent a message to the player, it should be displayed as a popup notification on the player’s screen
  and later be available in the notes section

John Doe 🕜 15:30 10 Sep 1920 Cash $100
⬇️ Description
John is a brave and curious investigator...
------------

HP 10/12 =======__
SAN 20/30 ======____
MP 5/10 ======____
LCK 55/100 ======____

------------

claustrophobia (phobia) 3 rounds | poisoned (poison) 5 rounds

------------
STATS
STR 50 CON 40 DEX 60 INT 70 POW 30 SIZ 80 APP 50 EDU 60
------------
⬇️ Skills
Repair 70%
Intimidate 50%
English 50%
Track 30%
Credit Rating 20%
Cthulhu Mythos 0%
--show more--
------------
⬇️ Compat skills
dodge 30%
Brawl 60%
Handgun 20%
Knife 1D4 + BD
Handgun 1D6 + BD
------------
⬇️ Items
Flashlight x1 | Pocket knife x1 | First aid kit x1
------------
⬇️ Spells
Vision of the future 4MP
------------
⬇️ Notes and messages
|---------|
|         |
|---------|