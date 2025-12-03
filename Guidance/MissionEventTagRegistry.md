# Mission Event Tag Registry

This asset is the single source of truth for every mission-related gameplay tag that the Mission Director listens to. It holds metadata such as scoring, UX strings, FX/MMSS hooks, and whether an event should trigger objective completion. Updating this asset keeps the director’s runtime behavior, analytics, and tag-driven failure conditions in sync.

## Editing the registry
- Each entry maps directly to `FSOTS_MissionEventTagDefinition`. Populate `EventTag`, `Category`, `Title`, `Description`, `ScoreDelta`, `ContextTags`, and the optional `FXTag`/`MusicTag` so runtime systems know how to react.
- The `bTriggersObjectiveCompletion` flag lets you define events that should update objectives (typically `true` for completion tags and `false` for purely informational markers).
- The registry asset lives at `/Game/DevTools/DA_MissionEventTagRegistry`. Use the helper script to seed or patch it by running:
  ```ps1
  python DevTools/python/write_files.py --source DevTools/python/chatgpt_inbox/mission_event_tag_registry_template.txt
  ```
  The template file documents sample entries; tweak it or craft a new chatgpt input to rerun the helper whenever you add/remove tags.

## Tag hygiene
- Every tag you register in the asset must be declared in `Config/DefaultGameplayTags.ini` so the tag system can load it at startup. Add entries under `Mission.State.*` and `Mission.Event.*` to keep the TagManager canonical.
- Run `DevTools/python/check_tag_spine.py` after modifying tags to validate the Tag Spine and catch unregistered emissions.

## Mission definition defaults
- `USOTS_MissionDefinition` now exposes `MusicTag_OnMissionStart`, `MusicTag_OnMissionCompleted`, and `MusicTag_OnMissionFailed`. Use these fields in your mission assets to request the correct track whenever the mission lifecycle reaches that stage.
- Keep the mission’s `FXTag_OnMission*` fields aligned with their music counterparts so designers can mix/match VFX and audio cues.
- When creating a new mission definition, include the registry’s canonical event tags inside objective `CompletionTags` (e.g., `Mission.Event.Objective.PrimaryCompleted`). That way the director knows which registry entry supplies scoring/FX/MMSS metadata.

## Validation
- After updating the registry or mission definitions, run the relevant DevTools checks (tag spine, mission definitions scanner, etc.) and launch the editor to verify the new events emit the expected FX/music and objectives move to the completed state.
