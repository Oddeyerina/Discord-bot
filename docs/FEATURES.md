# Features

The dashboard is the setup interface. Member slash commands are for using features after an administrator has configured them.

## Tickets

- **What it does:** Named panels can serve different kinds of tickets. A reason selects the support roles and follow-up questions; an optional priority appears on the ticket.
- **Where to configure it:** `/dashboard/tickets`. Create panels, choose a channel, configure reasons, support roles, priorities, auto responses, quick replies, the thread name pattern, a transcript channel, and the panel embed.
- **How to use it in Discord:** Click **Open Ticket**, choose a reason and, if offered, a priority. The bot creates a private thread in the panel channel, adds the opener and members of the chosen support roles, posts questions, and waits for **Done**. Done disables itself and pings those roles once. Support can **Claim**, change priority, use a quick reply, or **Close**; the opener can also close. Close archives and locks the thread and sends a plaintext transcript with a log embed.
- **Required permissions:** View Channels, Send Messages, Embed Links, Create Private Threads, Send Messages in Threads, Manage Threads, Read Message History, and permission to mention support roles.
- **Notes / limitations:** Discord private threads admit individual members, so the bot expands each support role to its members. Configure Server Members Intent for this. Ticket names may start with the reason emoji. Auto responses inspect the opener's first nonempty message. Missing threads are marked closed when the opener tries again and during hourly cleanup. Each panel keeps its own reasons, priorities, auto responses, and quick replies.

## Honeypot

- **What it does:** A decoy channel triggers a kick, ban, or timeout when a nonexempt user posts or reacts.
- **Where to configure it:** `/dashboard/honeypot` for the channel, action, whitelist, log channel, optional DM, message deletion, and embed.
- **How to use it in Discord:** Post the panel from the dashboard. The bot applies the action and sends a red log embed when triggered.
- **Required permissions:** View Channels, Send Messages, Embed Links, Manage Messages, Kick Members, Ban Members, or Moderate Members according to the selected action.
- **Notes / limitations:** Administrators, bots, and whitelisted roles are exempt.

## Reaction Roles

- **What it does:** Multiple named panels assign roles from reactions or a select menu.
- **Where to configure it:** `/dashboard/reaction-roles`; create panels with channels, styles, emoji-to-role mappings, and embeds.
- **How to use it in Discord:** React to a reaction panel, remove the reaction, or use a select panel to update roles.
- **Required permissions:** View Channels, Send Messages, Embed Links, Add Reactions, Manage Roles, and a bot role above the roles it assigns.
- **Notes / limitations:** Invalid reaction emoji are skipped and logged; a bad emoji does not stop the rest of a panel from posting.

## Levels

- **What it does:** Grants XP for eligible messages and awards configured roles at levels.
- **Where to configure it:** `/dashboard/levels` for XP, cooldown, ignored channels and roles, level roles, and the announcement embed.
- **How to use it in Discord:** Members use `/rank [user]` and `/leaderboard`. Level-up announcements post automatically.
- **Required permissions:** View Channels, Send Messages, Embed Links, Manage Roles, and Message Content Intent.
- **Notes / limitations:** Rank and leaderboard replies are ephemeral. The bot role must be above awarded roles.

## Welcome / Goodbye

- **What it does:** Posts configurable embeds when members join or leave, and can assign several auto roles on join.
- **Where to configure it:** `/dashboard/welcome`.
- **How to use it in Discord:** Messages and role assignments happen automatically. Welcome and goodbye messages include a user mention as content for a real ping.
- **Required permissions:** View Channels, Send Messages, Embed Links, Manage Roles, and Server Members Intent.
- **Notes / limitations:** The bot role must be above all auto roles.

## Sticky Messages

- **What it does:** Reposts an embed after channel activity so it stays near the bottom.
- **Where to configure it:** `/dashboard/sticky` for each channel, embed, cooldown, and optional role ping.
- **How to use it in Discord:** Use **Sticky now** for one channel or **Resend all stickies** to refresh every enabled channel.
- **Required permissions:** View Channels, Send Messages, Embed Links, Manage Messages, and permission to mention the configured role.
- **Notes / limitations:** `{role}` inserts the selected role mention. One role field currently controls both insertion and pinging.

## Temp Voice

- **What it does:** Creates a temporary voice channel when someone joins a hub and deletes it after the last member leaves.
- **Where to configure it:** `/dashboard/tempvoice` for hub, category, control text channel, name template, and default user limit.
- **How to use it in Discord:** While connected to the temporary channel, run `/tempvoice name <name>`, `/tempvoice limit <limit>`, `/tempvoice lock`, `/tempvoice unlock`, or `/tempvoice delete` in the control text channel. These require ownership. `/tempvoice claim` lets a connected member take ownership after the owner leaves.
- **Required permissions:** View Channels, Send Messages, Manage Channels, Move Members, and Manage Roles for permission overwrites.
- **Notes / limitations:** The new name preserves an existing leading emoji. Command replies are ephemeral; commands run outside the control channel are rejected.

## Sticky Roles

- **What it does:** Restores selected roles to returning members.
- **Where to configure it:** `/dashboard/sticky-roles` for enablement and excluded roles.
- **How to use it in Discord:** Roles are saved on leave and restored on rejoin.
- **Required permissions:** Manage Roles and Server Members Intent.
- **Notes / limitations:** The bot can restore only roles below its own role.

## Remembering Dates

- **What it does:** Announces saved birthdays and other recurring dates, with optional label-specific embeds.
- **Where to configure it:** `/dashboard/remembering` for channel, timezone, default embed, and per-label overrides.
- **How to use it in Discord:** Members use `/birthday set <day> <month> [label] [year]`, `/birthday remove [label]`, and `/birthday list`.
- **Required permissions:** View Channels, Send Messages, Embed Links.
- **Notes / limitations:** Command replies are ephemeral. Invalid dates are rejected; February 29 announces only in leap years. Dates are checked daily at 08:00 UTC using the configured local timezone.

## Information commands

- **What it does:** Shows available commands, member information, and server information.
- **Where to configure it:** No dashboard settings are needed.
- **How to use it in Discord:** `/help`, `/userinfo [user]`, and `/serverinfo` post public replies.
- **Required permissions:** View Channels and Send Messages.
- **Notes / limitations:** `/help` reflects the registered guild command tree.

## Polls

- **What it does:** Posts a native Discord poll with two to ten answers.
- **Where to configure it:** No dashboard settings are needed.
- **How to use it in Discord:** `/poll <question> <option1> <option2> [option3…option10] [duration] [multi]`.
- **Required permissions:** View Channels, Send Messages, Create Polls.
- **Notes / limitations:** Durations start at one hour. The posted poll is public; validation errors are ephemeral.

## Events

- **What it does:** Posts an event announcement, creates a Discord scheduled event, or both.
- **Where to configure it:** No dashboard settings are needed.
- **How to use it in Discord:** `/event create <title> <date> <time> [description] [type] [channel] [duration_minutes]`; types are **Message only**, **Discord event only**, and **Both**. Use `/event list` and `/event cancel <id>` to review and cancel.
- **Required permissions:** View Channels, Send Messages, Embed Links, Create Events, and Manage Events for scheduled events.
- **Notes / limitations:** Dates use `YYYY-MM-DD` and `HH:MM` in Europe/Berlin. Announcements are public; command confirmations are ephemeral.

## Stats

- **What it does:** Posts one live stats embed and edits it at the configured interval.
- **Where to configure it:** `/dashboard/stats` for channel, enabled state, interval, embed, and custom role counters.
- **How to use it in Discord:** Use **Post / Update now** in the dashboard to queue an immediate refresh. The bot updates automatically while enabled.
- **Required permissions:** View Channels, Send Messages, Embed Links, Server Members Intent, and Presence Intent for `{online}`.
- **Notes / limitations:** A deleted stats message is recreated. No voice channel names are changed. Custom role counter labels become `{role_count_<label_slug>}`, for example Artists becomes `{role_count_artists}`.

## Placeholders

Embeds use `{user}`, `{guild}`, `{membercount}`, `{level}`, `{label}`, `{age}`, and `{role}` where those values are available. The embed editor shows these tokens. In title, description, and footer text, a matching `#channelname` becomes a channel mention and a matching `@rolename` becomes a role mention. Unmatched names remain unchanged.

Stats embeds additionally support `{total_members}`, `{human_members}`, `{bot_members}`, `{online}`, `{in_voice}`, `{artist_count}`, `{verified_count}`, `{booster_count}`, `{boost_count}`, `{boost_level}`, `{boosts_needed}`, `{timestamp}`, and configured `{role_count_<label_slug>}` values. The artist and verified counts come from custom role counters with matching labels; otherwise they are zero.

## Permissions

| Permission or intent | Used by |
| --- | --- |
| View Channels, Send Messages | Panels, announcements, commands, stats |
| Embed Links | Panels, announcements, logs, stats |
| Read Message History | Ticket transcripts |
| Create Private Threads, Send Messages in Threads, Manage Threads | Tickets |
| Add Reactions | Reaction-role panels |
| Manage Messages | Honeypot deletion and sticky messages |
| Manage Roles | Reaction roles, level roles, welcome auto roles, sticky roles |
| Manage Channels, Move Members | Temp Voice |
| Kick Members, Ban Members, Moderate Members | Honeypot actions |
| Create Polls | Polls |
| Create Events, Manage Events | Discord scheduled events |
| Mention Everyone or mentionable support roles | Ticket and sticky role pings |
| Server Members Intent | Private ticket support membership, join and leave features, stats |
| Message Content Intent | XP, honeypot messages, sticky activity, ticket auto responses |
| Presence Intent | Online member stats |

## Dashboard pages

| Page | Configuration |
| --- | --- |
| `/dashboard` | Overview and recent tasks |
| `/dashboard/tickets` | Named ticket panels, reasons, priorities, responses, quick replies |
| `/dashboard/honeypot` | Decoy channel, action, whitelist, logging |
| `/dashboard/reaction-roles` | Named reaction and select panels |
| `/dashboard/levels` | XP, cooldowns, role rewards, announcements |
| `/dashboard/welcome` | Join and leave embeds, auto roles |
| `/dashboard/sticky` | Sticky channels, embeds, role pings |
| `/dashboard/tempvoice` | Voice hub and command control channel |
| `/dashboard/sticky-roles` | Role persistence and exclusions |
| `/dashboard/remembering` | Date announcements and label embeds |
| `/dashboard/stats` | Live statistics embed and counters |
