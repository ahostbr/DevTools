# FSOTS Profile Snapshot Guidance

This document keeps every `FSOTS_*` profile slice aligned with the subsystems that own them and the serialization order enforced by `FSOTS_ProfileSnapshot`/`USOTS_ProfileSubsystem`.

## Slice ownership and responsibilities
| Struct | Owning subsystem/module | Responsibility | Notes |
| --- | --- | --- | --- |
| `FSOTS_ProfileId` | `USOTS_ProfileSubsystem` (SOTS_ProfileShared) | Identifies saved slots (name + index) so the save/load flow can keep metadata keyed. | Used by profile UI, analytics, and DevTools exporters. |
| `FSOTS_ProfileMetadata` | `USOTS_ProfileSubsystem` | Captures display name, last played UTC, and total play seconds for save metadata. | Always written before any slice data so UI can show chronologically-sorted saves. |
| `FSOTS_CharacterStateData` | `USOTS_ProfileSubsystem` ↔ `USOTS_StatsComponent`/actor state | Persists player transform, stat table, movement tags, and equipped ability tags. | `BuildSnapshotFromWorld` pulls from the active pawn/Stats component; `ApplySnapshotToWorld` rehydrates transform/abilities. |
| `FSOTS_SerializedItem` | `SOTS_INV` (inventory bridge) | Represents a stackable item id + quantity for carried/stash arrays. | This struct is reused inside `FSOTS_InventoryProfileData`. |
| `FSOTS_ItemSlotBinding` | `SOTS_INV` inventory bridge / quick-slot wiring | Records a quick-slot index → item id mapping so the player can restore bindings. | Keep this lightweight; the inventory subsystem resolves `SlotIndex` semantics. |
| `FSOTS_GSMProfileData` | `USOTS_GlobalStealthManagerSubsystem` (GSM) | Stores alert level, current alert tier tag, and persistent stealth flags. | GSM reads/writes these tags during stealth transitions and mission loading. |
| `FSOTS_AbilityProfileData` | `SOTS_GAS_Plugin` / ability component | Tracks granted ability tags, ability ranks, and cooldown timers. | The GAS plugin shares this struct with Blueprint-exposed ability managers. |
| `FSOTS_SkillTreeProfileData` | `SOTS_SkillTree` | Holds unlocked skill nodes and unspent points for the shared skill tree system. | The Skill Tree subsystem applies these tags back to the data-driven tree when loading. |
| `FSOTS_InventoryProfileData` | `SOTS_INV` inventory bridge | Aggregates carried items, stash, and quick-slot bindings for an entire profile. | Populate using inventory components, restore via the inventory bridge. |
| `FSOTS_MissionProfileData` | `USOTS_MissionDirectorSubsystem` | Mirrors mission completion history, last mission id, and run metrics (score/duration). | The Mission Director pushes mission tags to the profile snapshot when runs end. |
| `FSOTS_MMSSProfileData` | `USOTS_MMSSSubsystem` | Records current music role tag, track id, and playback position for persistence. | Music subsystem uses this to resume appropriate tracks after loading a save slot. |
| `FSOTS_FXProfileData` | `USOTS_FXManagerSubsystem` | Stores FX-related toggles (blood, intensity, camera motion FX). | The FX manager respects these toggles whenever FX are triggered. |
| `FSOTS_ProfileSnapshot` | `USOTS_ProfileSubsystem` | Aggregates every slice and is the single save/load payload. | Shipping this struct to disk outlines serialization order—keep the order stable!

## Serialization order
`USOTS_ProfileSubsystem` treats the order of properties in `FSOTS_ProfileSnapshot` as the authoritative serialization order. Keep the following sequence intact when patching the struct or when adding/removing slices:
1. `Meta` (ID + metadata)
2. `PlayerCharacter` (transform, stats, tags)
3. `GSM` (global stealth state)
4. `Ability` (abilities/tiers)
5. `SkillTree` (unlocked nodes + points)
6. `Inventory` (carried/stash/quick slots)
7. `Missions` (mission history, scores, flags)
8. `Music` (MMSS role + track state)
9. `FX` (FX toggles)

This order is mirrored in `USOTS_ProfileSubsystem::BuildSnapshotFromWorld`, `ApplySnapshotToWorld`, `SaveProfile`, and `LoadProfile`. When you add a new slice you cannot reorder the existing entries; append the slice at the desired position and update all four methods so they read/write in lockstep.

## Adding a new profile slice
1. **Define the slice struct** in `Plugins/SOTS_ProfileShared/Source/SOTS_ProfileShared/Public/SOTS_ProfileTypes.h`. Keep the `USTRUCT` near the other `FSOTS_*` definitions so tooling (DevTools validators, serialization checks) can locate it easily.
2. **Add a property of that struct** to `FSOTS_ProfileSnapshot` at the appropriate point in the serialization order. Annotate the property with a comment explaining what subsystem owns the slice.
3. **Wire the slice into `USOTS_ProfileSubsystem`**: update `BuildSnapshotFromWorld` to populate the slice (usually by querying the owning subsystem/bridge), update `ApplySnapshotToWorld` to push snapshot data out, and ensure `SaveProfile`/`LoadProfile` still marshal the `FSOTS_ProfileSnapshot` in the same order.
4. **Notify the owning subsystem** so it can consume the slice (e.g., have the ability system apply `FSOTS_AbilityProfileData` during initialization). Add helper getters or replication hooks in that subsystem if needed.
5. **Update module includes/dependencies**: import any new headers at the top of `SOTS_ProfileTypes.h`, and if the slice introduces a new module dependency, add it to `Plugins/SOTS_ProfileShared/SOTS_ProfileShared.Build.cs`.
6. **Document the slice** in this guidance doc and any subsystem-specific README so other teams know which tags or data are governed by it.

### DevTools scaffolding for new slices
1. Update `DevTools/python/chatgpt_inbox/new_profile_slice_template.txt` with your slice name, owner details, and any supplementary instructions (the template already includes the structure and the `=== FILE ===` hints used by `write_files.py`).
2. Run:
   ```powershell
   python DevTools/python/write_files.py --source DevTools/python/chatgpt_inbox/new_profile_slice_template.txt
   ```
   This patches `SOTS_ProfileTypes.h` with a placeholder struct definition and snapshot property so you can start validation quickly.
3. Follow the steps above to hook the slice into the owning subsystem and update serialization helpers.

Keep this document in sync whenever a new `FSOTS_*` struct is added; it powers DevTools’ profile validators and the extended memory LAWs doc references this layout when analyzing snapshots.