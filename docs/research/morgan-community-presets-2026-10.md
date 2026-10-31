# Factory banks dwarf every other Morgan source

*Research, 2026-10-31, for the ML session; not a declared plan. Nothing was downloaded, no account was created and no terms were accepted.*

The plugin's own presets are the only large, well-established source, and the project already uses them. [`research/render_preset_panel.py`](../../research/render_preset_panel.py) (`candidates`) reads every non-`User/` `.xml` under `/Library/Audio/Presets/Neural DSP/Morgan Amps Suite` with the repo's parser ([`format/parser.py`](../../format/parser.py)) to build the three amps' menus that the training draws centre on; [`learn/pr12.py`](../../learn/pr12.py) does the same for PR12 only. The repo's [menu file](../set3-development-diagnostic-menus.json) (8 Oct 2026, before X) lists **108 factory presets: 44 SW50R, 34 PR12, 30 AC20**. 40% of today's training draws centre on them ([pipeline review](../ml-pipeline-review.md), step 6). Suite X, a free update from 28 Oct 2026, ships "more than 100 curated presets" ([Neural DSP](https://neuraldsp.com/news/introducing-morgan-amps-suite-x)); whether any are new is unknown until its folder is listed. Outside Neural DSP the known pool is small: **about 65 presets (four packs of 14–15, and 5 in one YouTube giveaway), of which only Omega Station's 14 are free with no licence stated**, plus unknown counts on PresetJunkie, soundlearn and Discord. No source mentions machine-learning use, and no community source states a licence.

## The rule each source is mapped onto

The project's licence and cost rule ([ML plan §5](ml-plan-2026-10.md#5-rules-for-every-step)): a source "with no licence stated" is fine; "Unclear or conflicting licence terms go to the user to check"; and "any other paid tool or service needs the user's yes". That cost clause names tools and services; a paid preset pack is treated the same way here.

## Neural DSP: one big bank, plus "a few" on Discord

| Source | Presets | Format | Terms (quoted) | Cost | Login | Size | §5 |
|---|---|---|---|---|---|---|---|
| [Installed factory and artist banks](https://neuraldsp.com/plugins/morgan-amps-suite) | 108: 27 Neural DSP, 80 in 14 artist folders, 1 Default | "encrypted XML" ([manual](https://images.equipboard.com/uploads/item/manual/129290/neural-dsp-morgan-amp-suite-manual.pdf)) | no public EULA found (presumably in the installer); product page: "Every preset is fully tweakable" | with the plugin, €99 (€69.30 on sale); 14-day trial | iLok | ~3.4 KB each (repo `samples/`); the plugin needs "400MB - 1GB of free storage" | in use; the user accepted the EULA at install; reading it is the open check |
| [Suite X bank](https://neuraldsp.com/news/introducing-morgan-amps-suite-x) | "more than 100"; overlap unknown | probably the same | as above | "free update for existing Morgan Amps Suite users" | iLok | not published | not a §5 matter; see the update risk below |
| [Neural DSP forum](https://unity.neuraldsp.com/c/plugins/18) | 0; two Morgan preset requests, neither with files ([one](https://unity.neuraldsp.com/t/anyone-have-presets-for-the-morgan-amp-suite/13873)) | `.xml` (other plugins) | "Content you submit to the forum belongs to you, and you decide what permission to give others for it." ([ToS](https://unity.neuraldsp.com/tos)) | free | reading is public | ~5 KB | nothing to use |
| [Discord presets channel](https://discord.com/channels/795690608181641257/800812669887709204) | "A few" (moderator, 2024) | unknown | unknown (channel unread) | free | a Discord account and a new invite; the last one reads "Invite is expired." | unknown | no terms seen; joining is the user's call |

[Cortex Cloud](https://neuraldsp.com/pages/terms-of-use-cortex-cloud) holds none: "the cloud is specifically for the Quad Cortex" ([forum](https://unity.neuraldsp.com/t/preset-sharing/8259)).

The researchers' sources disagree on the artists. Mix named Neil Zaza, Pete Thorn and Rabea Massaad ([Mix](https://www.mixonline.com/technology/neural-dsp-morgan-amps-suite-a-mix-product-of-the-week)); the X news names Charlie Robbins, Jack Gardiner, Massaad and Joshua De La Victoria. The installed menu has folders for all six, so both lists look partial, not conflicting. The manual says "encrypted XML"; headdirt's tool calls the files binary JUCE ValueTree data ([headdirt](https://raw.githubusercontent.com/headdirt/ndsp_preset_tool/main/README.md)) and toneparse "a proprietary binary format" ([toneparse](https://raw.githubusercontent.com/vian21/toneparse/master/README.md)). The project's parser reads them either way.

**Update risk.** Neural DSP says X "retains the original plugin's AC20, PR12 and SW50R amplifier models", but re-render a few stored settings before relying on it. The builds record `plugin_version` and stop if it changes ([`learn/pretrain_set.py`](../../learn/pretrain_set.py): "the recipe changed since the first shard"). Parallax X installed as a separate plugin and folder ([staff post](https://unity.neuraldsp.com/t/parallax-x-is-out-now/14451)). If Morgan X does too, the hard-coded preset path (in `research/render_preset_panel.py`, `learn/pr12.py` and four other scripts) will miss X's presets, and the plugin identity in `packs/morgan/manifest.json` (subtype `NMAS`) may change.

**Keep community packs out of the factory folder.** Omega Station's page says to "Extract the zip file into your presets folder". Both readers take every non-`User/` `.xml` there as `factory:`, so a pack installed that way would silently join every menu and the draws. Keep packs elsewhere, or under `User/`.

## Outside Neural DSP: about 65 known presets, mostly paid or unread

| Source | Presets | Format | Terms (quoted) | Cost | Login | Size | §5 |
|---|---|---|---|---|---|---|---|
| [Omega Station, Gumroad](https://omegastation.gumroad.com/l/morganampstraddoom) (doom; 77 sales) | 14 | `.xml` in a zip | none on the page | €0, pay what you want | Gumroad checkout, probably an email | 19 KB | fine (no licence stated); fetching is the user's call |
| [Karl Golden](https://karlgolden.org/morgan-amp-suite-presets) | 15 | "15 x XML Files" | "All sales of digital products are final" | £4.99, in stock on 31 Oct (normally £9.99) | not stated | not stated | paid: user's yes |
| [Juan Antonio Music](https://www.juanantoniomusic.com/product-page/morgan-amps-suite-juan-antonio-presets) | 15, but its text says "Archetype Plini X" | not stated | "All sales on presets are final and non-refundable." | $15 | the site has "Log In" | not stated | which plugin is unclear: user's check; paid: user's yes |
| [Ko-fi](https://ko-fi.com/s/16de62d32e) | 15 + a PDF (search snippet only) | `.xml` | search snippet: no refunds | unclear | page blocked | not stated | user's check |
| [Hideaki Yamakado, YouTube](https://www.youtube.com/watch?v=5xV9s8G_R8E) | 5, "[Free Download]" | unknown | description unread | free (title) | unknown | unknown | read the description first |
| [soundlearn, YouTube](https://www.youtube.com/watch?v=VKz6TNB5Iy4) | unknown | unknown | description unread | free (title) | unknown | unknown | probably gone: its [Gumroad](https://soundlearn.gumroad.com/) lists no Morgan item |
| [PresetJunkie](https://www.presetjunkie.com/) | unknown; it advertises "Thousands of Presets" across Neural DSP plugins | Neural DSP presets | footer: "© 2025 Preset Junkie. All rights reserved." | "100% Free Forever" | an account even to browse | unknown | user's check |
| [Gig Performer rackspace](https://community.gigperformer.com/t/ndsp-morgan-amps-suite-complete/22454) | 0 confirmed (a control layout for all three amps; saved sounds not stated) | `.rackspace`, not `.xml` | none stated | free file | not stated | 1.8 MB | needs Gig Performer, a paid tool: user's yes |

The known total, 14 + 15 + 15 + 15 + 5 = 64, is about 65; without Juan Antonio and Ko-fi it is about 35.

Elsewhere is empty. About 1,200 r/NeuralDSP comments mentioning "morgan" (Dec 2023 – Mar 2026) and the stickied [presets thread](https://www.reddit.com/r/NeuralDSP/comments/p86qh2/presets_thread/) hold no Morgan file, and [GitHub](https://github.com/search?q=%22Morgan+Amps+Suite%22+extension%3Axml&type=code) returned 0. Searches of Gearspace, Sevenstring, The Gear Forum, The Gear Page, Ultimate Guitar and the Fractal forum found no Morgan preset thread. No Discord export turned up. A now-removed Tone3000 page held amp captures, not plugin presets, and Worship Tutorials' "MRGN" packs capture real Morgan amps for hardware ([Worship Tutorials](https://worshiptutorials.com/product/mrgn-ac20-dlx-tone-match-patches-line-6-fractal-kemper-tonex/)). Omega Station is the only seller with visible sales (77).

The researchers disagree on Ko-fi: one read that it "sells" the pack, the other "possibly pay-what-you-want" and "Sold Out". One advised asking sellers first ("Silence is not permission"); §5 does not require that.

## Song tones: two named after songs, one artist tone, all installed

| Preset (installed amp) | Target, per [Sound On Sound](https://www.soundonsound.com/reviews/neural-dsp-morgan-amps-suite) |
|---|---|
| Blue Hotel (SW50R) | "Chris Isaak cleans" |
| Slow Dancing Bell Tone (PR12) | "John Mayer's singing strat" |
| Red Special Rhythm (AC20) | "Brian May's crunch" |

All three are factory presets, already installed. Sound On Sound describes each at the artist level; the record links come only from the names. "Blue Hotel" is a Chris Isaak song, and "Slow Dancing Bell Tone" points to John Mayer's "Slow Dancing in a Burning Room". Red Special is Brian May's guitar, not a record. No community file found targets a record, but preset names in the unread sources (YouTube, PresetJunkie, Discord) could add some. The rest is video, such as a Sleep Token "Emergence" solo ([Reddit](https://www.reddit.com/r/NeuralDSP/comments/1je683k/)), or genre-level, like Omega Station's Black Sabbath-tuning variants.

## What this means for the ML session

- **Pool sizes:** 108 factory centres in use. Suite X has "more than 100", overlap unknown; its artists all have folders already installed. Outside Neural DSP there are about 65 known: 14 free with no licence stated, about 45 paid or unclear, and 5 in an unread giveaway. PresetJunkie, soundlearn and Discord counts are unknown. Mostly genre variety.
- **Clear under §5, no payment:** Omega Station only; fetching it is the user's decision.
- **Need the user's check:** PresetJunkie, Juan Antonio (which plugin), Ko-fi, the YouTube giveaways (descriptions unread).
- **Need the user's yes (paid):** Karl Golden, Juan Antonio, Ko-fi if paid, and Gig Performer for the rackspace.
- **Discord:** joining needs an account and a new invite; the user's call.
- **Suite X update:** not a §5 matter; a parity check first, since builds stop when the plugin version changes.
- **Any pack:** keep it out of the factory folder.
- **Open gaps:**
  - the EULA text;
  - X's exact count, per-amp split, overlap and folder;
  - PresetJunkie behind a login;
  - YouTube descriptions unread (rate-limited), and Ko-fi unread (blocked);
  - GitHub's zero, which was not re-checked;
  - the TGF, Gearspace and [JustinGuitar](https://community.justinguitar.com/t/neural-dsp-morgan-amp-suite/269530) Morgan threads, not read page by page;
  - the Facebook "Neural DSP Users" files page (needs a login);
  - Honest Amp Sim Reviews' Preset Vault (HTTP 503);
  - r/NeuralDSP after 29 Mar 2026.
