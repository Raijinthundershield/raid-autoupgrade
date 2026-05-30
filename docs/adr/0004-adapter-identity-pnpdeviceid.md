---
status: accepted
---

# Identify network adapters by PNPDeviceID, not DeviceID

The user picks one or more **Adapters** to disable during Count, and that selection is persisted in `settings.selected_adapters` so it survives across sessions. The selection stores a scalar identity that we resolve against the live adapter list each time Count runs.

We originally exposed and persisted the WMI `Win32_NetworkAdapter.DeviceID`. That value is only an **enumeration index** (e.g. `"3"`) — it shifts when an adapter is added or removed, on driver re-enumeration, and across some reboots. A persisted selection therefore rots silently: a later Count resolves the stale index to a *different* adapter or to nothing, so the wrong interface (or none) is disabled and the trick can run while still Online. This was the latent cause behind a reported "network did not turn off" incident.

We switch the persisted/exposed identity to `PNPDeviceID` — the Windows device-instance path (e.g. `PCI\VEN_8086&DEV_1539&...`). It is always present on physical adapters and stable across reboots, add/remove, and ordinary driver updates. `NetworkManager` resolves the toggle target by matching `PNPDeviceID` in Python over the live adapter list, rather than issuing a WQL query keyed on it (the value contains backslashes that would need escaping). The frontend treats the identity as opaque and never renders it as a raw DOM id.

## Considered options

- **PNPDeviceID (chosen)** — most stable identity for a physical adapter; survives the failure modes above. Cost: an ugly string, so matching happens in Python and the value is never used directly as a DOM id or unescaped WQL key.
- **GUID (NetCfgInstanceId)** — stable *and* clean (DOM/WQL-safe), but can be null on some adapters and is regenerated on a full driver uninstall/reinstall. Marginally less bulletproof for no structural gain.
- **MAC address** — clean and stable for Ethernet, but Wi‑Fi MAC randomization and duplicate MACs on virtual adapters make it drift or collide for other users.
- **Adapter Name** — human-readable but renamed by driver updates and not unique across identical NICs.
- **Keep DeviceID + auto-heal** — re-match a stale selection by a secondary key and rewrite the cached id. Preserves the contract but adds a re-matching code path to maintain instead of removing the instability at the source.

## Consequences

- Existing cached `selected_adapters` hold old DeviceIDs and will not resolve after the switch. The user reselects their adapter **once**; thereafter the selection is durable. No automatic migration is provided — the prior selections were already unreliable.
- `NetworkManager.toggle_adapter` resolves its target by iterating the live adapter list and matching `PNPDeviceID`, decoupling the public identity from the WMI query key.
- If a future adapter type reports no usable `PNPDeviceID`, revisit GUID as the fallback identity.
