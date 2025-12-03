# Alert Transition Tagging Guidance

This guide ensures that every AI alert/detection transition emits a canonical TagManager tag, keeping the Perception and Stealth pipelines synchronized.

## Canonical tags
- Use the `USOTS_NoiseTagRegistry` asset (`/Game/SOTS/Perception/DA_NoiseTagRegistry_Global`) to look up `SOTS.Noise.*` tags.
- Resolve tags through `SOTSNoiseTagRegistryHelpers::ResolveNoiseTag(World, RequestedTag)` (the registry also doubles as a document of every accepted noise/detection tag).

## Emitting tags
1. When a perception component flips into `ESOTS_PerceptionState::Alerted`, push `SOTS.Noise.Transition.Alert` into TagManager on the relevant actor. This is the tag every rest-of-game instrumentation should look for before treating an alert transition as “real.”
2. When a noise event escalates a guard’s detection tier (e.g., moving from Suspicious to Alert or Detected), emit `SOTS.Noise.Transition.Detection` so downstream systems (stealth HUD, mission director, etc.) can react consistently.
3. Always call into `SOTS_GetTagSubsystem(WorldContext)` or `USOTS_TagLibrary::AddTagToActor` instead of manually touching `FGameplayTagContainer`s to keep writes centralized.

## Validation
- Run `DevTools/python/check_tag_spine.py` after adding new noise/detection tags to make sure they’re registered via the TagManager’s spine.
- Inspect `/Game/SOTS/Perception/DA_NoiseTagRegistry_Global` to verify that every tag you intend to emit is listed, documented, and tagged with `bIsAlertTransition` or `bIsDetectionTag` as appropriate.
