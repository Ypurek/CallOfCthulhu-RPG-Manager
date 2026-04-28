tasks to implement:

- [x] make sure player in the session menu sees
    - name of the session
    - in game day and time (it should be updated automatically when the keeper changes it)
    - the full character sheet (all info should be updated automatically when the keeper changes it)
    - character edit button (opens wizard)
    - public session notes
    - own player notes related to the session (private, only visible to the player)
    - no extra containers, spaces. it should look good on mobile
- [ ] as a player, I want to see the notification icon in the scenario, near day and time
- [ ] as a keeper, I want to send messages to players in the session. they should be notified immediately
- [ ] as a keeper I want to see checkboxes near character skills to mark ones need to be updated after the session. player should not see them
- [ ] for the keeper in the session add button to call a popup for each character to add fast status effect, phobia,
  madness, mania. They can be picked from the list or added manually.
    - specific status effect should be added - deep wound. on tap on it the popup with the guide should be opened. deep
      wound can be treated in case of extremely successful heal or heal for 50% or more hp.
    - if character loses 50% of max hp or more in one hit, deep wound should be added automatically.
    - when the deep wound is added, the character should be notified and roll for CON to avoid passing out.
    - character with deep wound should roll for CON every week (7 days). in case of success can restore 1D3 hp
- [ ] the list of effects, phobias, madness, mania should be stored in the database and should be editable by the admin
- status effects displayed in the character card as badges under the name
- [ ] automatic logic should be added - characters without the "deep wound" status effect should restore 1 hp every day
  as soon as the next day starts
- [ ] automatic logic should be added - if the character has 0 hp, the "near death" status effect should be added
  automatically. player should be notified and roll for CON each turn to avoid death
- [ ] automatic logic should be added -in case character looses 5 or more SAN at once, the "psychological trauma" status
  effect should be added. player should be notified and roll for INT. if roll <= INT, roll D10 for madness.
- keeper can add/remove status effects, phobias, madness, mania manually at any time
- TODO: make the /snapshot/ api to work only with json data, no html at all.