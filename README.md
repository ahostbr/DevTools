PassType names (official)

For any plugin SOTS_XYZ, we’ll use:

PLAN – Design-only, no files

SPINE – Core law + types/config (internal spine)

BRIDGE – Integration with other spines/plugins

TOOLS – DevTools scripts, reports, QA helpers

BUNDLE – Omnibus/aggregator workflows (Prompt 25 style)

Think of them like layers:

PLAN – What are we doing?

SPINE – What’s the plugin’s core shape?

BRIDGE – How does it talk to the rest of SOTS?

TOOLS – How do we inspect & debug it?

BUNDLE – How do we one-click orchestrate everything for this plugin?

What each PassType means in practice
1) PLAN – design-only

No [SOTS_DEVTOOLS] block.

No code.

Just:

V2_1–25 mapping for that plugin.

What files exist / should exist.

How later passes (SPINE/BRIDGE/TOOLS/BUNDLE) will be structured.

Example ask:

“Give me SOTS_INV PLAN (design-only, no code).”

2) SPINE – plugin’s internal spine

Single [SOTS_DEVTOOLS] pack for:

Plugin law comments.

Core types, config DAs, Profile slice.

Minimal DevTools hooks if needed (e.g. basic sanity checks).

Focused on inside the plugin, not cross-plugin wiring.

Example ask:

“Generate SOTS_Parkour SPINE as a [SOTS_DEVTOOLS] pack (core types + config only, no DevTools analytics yet).”

3) BRIDGE – integration / wiring

[SOTS_DEVTOOLS] pack that:

Wires this plugin into TagManager, ProfileShared, Stats, Stealth, etc.

Adjusts Build.cs / includes / subsystems as needed.

Focused on how SOTS_XYZ plugs into the rest of the suite, not devtools scripts themselves.

Example ask:

“Run SOTS_INV BRIDGE – I want the pack that wires inventory into TagManager, ProfileShared, and Stats, no analytics yet.”

4) TOOLS – devtools, analytics, QA

[SOTS_DEVTOOLS] pack(s) that:

Add Python scripts, config JSON, log formats.

Provide audits, reports, health checks for this plugin.

This is where most of the DevTools Python lives for that plugin.

Example ask:

“Give me SOTS_INV TOOLS – a pack that adds inventory audits and simple health reports, no bundles yet.”

5) BUNDLE – omnibus/aggregator (Prompt 25-style)

[SOTS_DEVTOOLS] pack(s) that:

Create orchestrator scripts (“Map Diagnostics Bundle”, “Full Plugin Health Sweep”, etc.).

Add menu entries in sots_tools.py for one-click runs.

Must obey the omnibus law: design-only first if big, then implementation in small slices.

Example ask:

“Now I want SOTS_Parkour BUNDLE – design-only first, then a pack for the Map Diagnostics Bundle like Prompt 25.”

How you’ll use it in conversation

From now on, you can talk to me like this:

“Let’s do SOTS_TagManager PLAN.”

“Okay, now SOTS_TagManager SPINE as a single write_files pack.”

“Later, we’ll come back for SOTS_TagManager TOOLS.”

“For inventory: generate SOTS_INV BRIDGE only.”

“Parkour vNext: we already finished SPINE, now I want TOOLS, then a BUNDLE pass.”

When you say:

“run SOTS_INV PassType X”

I’ll interpret it as:

SOTS_INV PLAN → design spec only.

SOTS_INV SPINE → [SOTS_DEVTOOLS] pack for internal spine.

SOTS_INV BRIDGE → pack for wiring into other systems.

SOTS_INV TOOLS → pack for DevTools scripts/reports.

SOTS_INV BUNDLE → pack for aggregator workflows (like Prompt 25).

If you want, I can give you a tiny laws-file snippet that declares these PassTypes so they’re “canon,” but we can already start using the names right away.