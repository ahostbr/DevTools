# SOTS Steam Leaderboard Guidance

This guidance keeps mission-result tags, SOTS-defined leaderboards, and DevTools creation prompts aligned so submitting scores stays deterministic.

## Mission result → leaderboard tag mapping
Every `USOTS_SteamLeaderboardDefinition` lists a `FGameplayTagContainer Tags`. `USOTS_SteamLeaderboardsSubsystem::SubmitMissionResultToLeaderboards` builds a tag set that includes:
- `Result.MissionTag` (e.g., `SAS.Mission.CastleInfiltration`).
- `Result.DifficultyTag` (e.g., `SAS.Difficulty.Hard`).
- Hard-coded challenge tags for guard-free/alert-free/perfect stealth runs (`SAS.Mission.NoKills`, `SAS.Mission.NoAlerts`, `SAS.Mission.PerfectStealth`).
- Everything inside `Result.AdditionalTags` (use this to whitelist modifiers such as `SAS.Mission.Modifier.HiddenCache`).

A leaderboard definition is matched if its `Tags` are a subset of the mission result tags. This lets designers create scoreboards scoped to mission + difficulty + modifiers simply by authoring the right tag combinations in the registry.

## DevTools scaffolding for leaderboard definitions
New leaderboard definitions live in `USOTS_SteamLeaderboardRegistry`. Use the DevTools helper with the template below to create or update entries:

```
python DevTools/python/write_files.py --source DevTools/python/chatgpt_inbox/leaderboard_definition_template.txt
```

The template sits next to this doc and includes sample leaderboards that combine mission/difficulty tags, Steam API names, and `bMirrorToSteam` toggles. Edit the prompt (swap `InternalId`, `Tags`, `SteamApiName`, etc.) before rerunning so the generated `.uasset` reflects your mission.

## Online validation helper
`USOTS_SteamLeaderboardsSubsystem` exposes `GatherOnlineInterfacesForLeaderboards`, which wraps:
- `ShouldUseOnlineLeaderboards()` (settings + Steam integration toggles).
- `GetOnlineLeaderboardsInterface()`, `GetOnlineIdentityInterface()`, and `GetPrimaryUserId()`.

Call this helper before any Steam API interaction (`WriteLeaderboards`, `ReadLeaderboards`, etc.) so you log consistent warnings for missing interfaces and skip retries cleanly. It also ensures `bUseSteamForLeaderboards` is respected in one place instead of being rechecked every time.
