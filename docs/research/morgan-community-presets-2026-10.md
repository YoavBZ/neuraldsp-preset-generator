# Factory banks dwarf every other Morgan source

*Research, 2026-10-31, for the ML session; not a declared plan. Nothing was downloaded, no account was created and no terms were accepted.*

The plugin's own presets are the only large, well-established source, and the project already uses them. [`learn/pr12.py`](../../learn/pr12.py) reads every non-`User/` `.xml` under `/Library/Audio/Presets/Neural DSP/Morgan Amps Suite` with [`format/parser.py`](../../format/parser.py), and the repo's [menu file](../set3-development-diagnostic-menus.json) (8 Oct 2026, before X) lists **108 factory presets: 44 SW50R, 34 PR12, 30 AC20**. 40% of today's training draws centre on them ([pipeline review](../ml-pipeline-review.md), step 6). Suite X, a free update from 28 Oct 2026, ships "more than 100 curated presets" ([Neural DSP](https://neuraldsp.com/news/introducing-morgan-amps-suite-x)); whether any are new is unknown until its folder is listed. Outside Neural DSP the pool is small: **four packs of 14–15 presets (one free) plus a few unread YouTube giveaways, roughly 35–65 presets**. No source mentions machine-learning use, and no community source states a licence.

## Neural DSP offers one big bank and nothing else

"§5" below is the project's rule ([ML plan §5](ml-plan-2026-10.md)): "no licence stated" is fine, "unclear or conflicting licence terms go to the user to check", and paying needs the user's yes.

| Source | Presets | Format | Terms (quoted) | Cost | Login | Size | §5 |
|---|---|---|---|---|---|---|---|
| [Installed factory and artist banks](https://neuraldsp.com/plugins/morgan-amps-suite) | 108: 27 Neural DSP, 80 in 14 artist folders, 1 Default | "encrypted XML" ([manual](https://images.equipboard.com/uploads/item/manual/129290/neural-dsp-morgan-amp-suite-manual.pdf)) | EULA only in the installer; product page: "Every preset is fully tweakable" | with the plugin, €99 (€69.30 on sale); 14-day trial | iLok | ~3.4 KB each (repo `samples/`) | in use; EULA unread |
| [Suite X bank](https://neuraldsp.com/news/introducing-morgan-amps-suite-x) | "more than 100"; overlap unknown | probably the same | as above | "free update for existing Morgan Amps Suite users" | iLok | not published | update is the user's call |
| [Neural DSP forum](https://unity.neuraldsp.com/c/plugins/18) | 0; the one Morgan [request](https://unity.neuraldsp.com/t/anyone-have-presets-for-the-morgan-amp-suite/13873) has no files | `.xml` (other plugins) | "Content you submit to the forum belongs to you, and you decide what permission to give others for it." ([ToS](https://unity.neuraldsp.com/tos)) | free | reading is public | ~5 KB | nothing to use |
| [Discord presets channel](https://discord.com/channels/795690608181641257/800812669887709204) | "A few" (moderator, 2024) | unknown | none found | free | Discord; last invite "Invite is expired." | unknown | user's check |

[Cortex Cloud](https://neuraldsp.com/pages/terms-of-use-cortex-cloud) holds none: "the cloud is specifically for the Quad Cortex" ([forum](https://unity.neuraldsp.com/t/preset-sharing/8259)).

The notes disagree on the artists. Mix named Neil Zaza, Pete Thorn and Rabea Massaad ([Mix](https://www.mixonline.com/technology/neural-dsp-morgan-amps-suite-a-mix-product-of-the-week)); the X news names Charlie Robbins, Jack Gardiner, Massaad and Joshua De La Victoria. The installed menu has folders for all six, so both lists look partial, not conflicting. The manual says "encrypted XML", two community parsers say binary JUCE ValueTree data ([headdirt](https://raw.githubusercontent.com/headdirt/ndsp_preset_tool/main/README.md), [toneparse](https://raw.githubusercontent.com/vian21/toneparse/master/README.md)); the project's parser reads them either way.

Update risk: Neural DSP says X "retains the original plugin's AC20, PR12 and SW50R amplifier models", but re-render a few stored settings before relying on it. Parallax X installed as a separate plugin and folder ([staff post](https://unity.neuraldsp.com/t/parallax-x-is-out-now/14451)); if Morgan X does too, `learn/pr12.py`'s path will miss X presets.

## Outside Neural DSP, about 35–65 presets, mostly paid or unread

| Source | Presets | Format | Terms (quoted) | Cost | Login | Size | §5 |
|---|---|---|---|---|---|---|---|
| [Omega Station, Gumroad](https://omegastation.gumroad.com/l/morganampstraddoom) (doom; 77 sales) | 14 | `.xml` in a zip | none on the page | €0, pay what you want | Gumroad checkout, probably an email | 19 KB | fine; fetching is the user's call |
| [Karl Golden](https://karlgolden.org/morgan-amp-suite-presets) | 15 | "15 x XML Files" | "All sales of digital products are final" | £4.99 | not stated | not stated | user's yes |
| [Juan Antonio Music](https://www.juanantoniomusic.com/product-page/morgan-amps-suite-juan-antonio-presets) | 15, but text says "Archetype Plini X" | not stated | "All sales on presets are final and non-refundable." | $15 | site has "Log In" | not stated | user's check and yes |
| [Ko-fi](https://ko-fi.com/s/16de62d32e) | 15 + PDF (snippet) | `.xml` | snippet: no refunds | unclear | page blocked | not stated | user's check |
| [Hideaki Yamakado, YouTube](https://www.youtube.com/watch?v=5xV9s8G_R8E) | 5, "[Free Download]" | unknown | unread | free (title) | unknown | unknown | user's check |
| [soundlearn, YouTube](https://www.youtube.com/watch?v=VKz6TNB5Iy4) | unknown | unknown | unread | free (title) | its [Gumroad](https://soundlearn.gumroad.com/) lists no Morgan item | unknown | probably gone |
| [PresetJunkie](https://www.presetjunkie.com/) | unknown | Neural DSP presets | footer: "© 2025 Preset Junkie. All rights reserved." | "100% Free Forever" | account even to browse | unknown | user's check |
| [Gig Performer rackspace](https://community.gigperformer.com/t/ndsp-morgan-amps-suite-complete/22454) | 1, all three amps | `.rackspace`, not `.xml` | none stated | free | not stated | 1.8 MB | fine; needs Gig Performer |

Elsewhere is empty. About 1,200 r/NeuralDSP comments mentioning "morgan" and the stickied [presets thread](https://www.reddit.com/r/NeuralDSP/comments/p86qh2/presets_thread/) hold no Morgan file, [GitHub](https://github.com/search?q=%22Morgan+Amps+Suite%22+extension%3Axml&type=code) returned 0, and no Discord export turned up. [Tone3000](https://www.tone3000.com/tones/morgan-amp-suite-63418) holds amp captures, and Worship Tutorials' "MRGN" packs capture real Morgan amps for hardware ([Worship Tutorials](https://worshiptutorials.com/product/mrgn-ac20-dlx-tone-match-patches-line-6-fractal-kemper-tonex/)). Omega Station is the only seller with a track record.

The notes disagree twice: one saw Karl Golden's page say "Out of stock", the other a £4.99 cart; one says Ko-fi "sells" the pack, the other "possibly pay-what-you-want" and "Sold Out". One researcher advises asking sellers first ("Silence is not permission"); §5 already accepts no-licence sources.

## Song tones: three factory presets, no community files

| Preset (installed amp) | Target, per [Sound On Sound](https://www.soundonsound.com/reviews/neural-dsp-morgan-amps-suite) |
|---|---|
| Blue Hotel (SW50R) | "Chris Isaak cleans" |
| Slow Dancing Bell Tone (PR12) | "John Mayer's singing strat" |
| Red Special Rhythm (AC20) | "Brian May's crunch" (an artist, not a record) |

All three are already installed. Nothing else targets a record: the rest is video, such as a Sleep Token "Emergence" solo ([Reddit](https://www.reddit.com/r/NeuralDSP/comments/1je683k/)), or genre-level, like Omega Station's Black Sabbath-tuning variants.

## What this means for the ML session

- **Pool sizes:** 108 factory centres in use; Suite X "more than 100", probably mostly the same; outside, 14 free, about 45 paid or unclear, 5+ in unread giveaways, PresetJunkie unknown. At most about 65 new centres, mostly genre variety.
- **Clear under §5, no payment:** Omega Station and the rackspace; fetching either is the user's decision.
- **Need the user's check:** PresetJunkie, Juan Antonio, Ko-fi, the YouTube giveaways, Discord.
- **Need the user's yes:** Karl Golden, Juan Antonio, Ko-fi if paid, and the Suite X update (parity check first).
- **Open gaps:** the installer EULA text; X's exact count, per-amp split, overlap and folder; PresetJunkie behind a login; YouTube descriptions unread (rate-limited); Ko-fi unread (blocked).
