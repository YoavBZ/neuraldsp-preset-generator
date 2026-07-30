# Getting a preset into the plugin

A written `.xml` file is not the deliverable — **hearing it is**. Always finish
the job by putting the preset where the plugin will find it, then telling the
user exactly what to click.

## Find the user preset folder

Don't hard-code a path. Locate it, because it varies by plugin name and version:

```bash
# macOS
ls -d ~/Library/Audio/Presets/Neural\ DSP/*/User 2>/dev/null

# Windows (from Git Bash / WSL)
ls -d "$USERPROFILE"/Documents/Neural\ DSP/*/User 2>/dev/null

# Linux (plugin runs under Wine, or a bridged host)
ls -d ~/Documents/Neural\ DSP/*/User 2>/dev/null
```

Pick the directory whose plugin name matches the pack you generated for
(`Morgan Amps Suite` for pack `morgan`). If nothing matches, ask the user where
their presets live rather than guessing — and if they tell you, note it so you
don't have to ask again.

## Write there directly

Once you know the folder, point `--out` at it instead of copying afterwards:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/apply_spec.py" \
  --template TEMPLATE.xml --spec /tmp/spec.json --strip-irs \
  --out ~/Library/Audio/Presets/Neural\ DSP/Morgan\ Amps\ Suite/User/"Hotel California Lead.xml"
```

The file name is what shows up in the plugin's preset browser, so name it the
way the user would look for it. The preset's internal `name` field (set from
the spec) and the file name should match.

## Confirm before overwriting

`apply_spec.py` refuses to overwrite an existing `--out` without `--force`.
That guard matters most here: the user preset folder is the one place where a
silent overwrite destroys work they care about. If the name is taken, ask
whether to replace it or pick another name.

## Close the loop

End with the two things the user actually needs:

> Wrote **Hotel California Lead** to your Morgan Amps Suite user presets.
> Open the plugin → preset browser → **User** → *Hotel California Lead*.
> If it's already open, hit the browser's refresh or reopen the plugin.

If the plugin was running while you wrote the file, it may need a rescan before
the preset appears. Say so — otherwise the user concludes it didn't work.
