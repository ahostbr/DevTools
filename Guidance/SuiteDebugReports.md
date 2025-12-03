# Suite Debug Report Filters

`USOTS_SuiteDebugSubsystem` now drives its logging through a configurable set of `FSOTS_SuiteDebugReport` entries. Each entry carries a `ReportId`, display name, and a `bIncludeInDump` flag so that DevTools can drop noise from specific subsystems without touching code.

## Where to edit filters
- The canonical asset is `/Game/DevTools/DA_SuiteDebugReports`. It lists every supported report (Global Stealth, Mission Director, Music, Tag Manager, FX, Inventory, Stats, Abilities) and the default `bIncludeInDump` state.
- After the asset is touched in editor, rerun `ReloadSuiteDebugReports` (Blueprint or log console) to refresh the runtime toggles without restarting the game.
- Use the `DevTools/python/write_files.py` helper to patch the asset via text. For example, summarizing the current asset format in `DevTools/python/chatgpt_inbox/suite_debug_reports.txt` produces a quick skeleton that can be pushed with a single command.

## How filtering works
1. `USOTS_SuiteDebugSubsystem::Initialize` registers provider lambdas for each report ID so the subsystem can build each summary string on demand.
2. The subsystem loads or falls back to `FSOTS_SuiteDebugReport` metadata (DisplayName + bIncludeInDump) from the asset before emitting logs.
3. When `DumpSuiteStateToLog` runs, it walks the metadata list and only prints lines whose `bIncludeInDump` flag is `true`. Changing that flag in the asset changes the log output instantly (after a reload).

## DevTools workflow
1. Run `python DevTools/python/write_files.py --source chatgpt_inbox/suite_debug_reports.txt` (or a similar prompt) to regenerate the asset with the desired toggles.
2. Use `ReloadSuiteDebugReports` from the `USOTS_SuiteDebugSubsystem` Blueprint library or via `ce ReloadSuiteDebugReports` console command to apply the new configuration.
3. Use the logged `ReportId` names (GlobalStealth, MissionDirector, etc.) to reference filters in other DevTools scripts or automation.
