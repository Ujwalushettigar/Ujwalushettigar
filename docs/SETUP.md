# Setup guide

## Folder structure

The repository must be named exactly `Ujwalushettigar` (same as the username) and be public. Its root looks like this:

```
Ujwalushettigar/
├── README.md
├── .github/
│   └── workflows/
│       └── snake.yml
├── assets/
│   ├── hero.svg
│   ├── boot.svg
│   ├── about.svg
│   ├── architecture.svg
│   ├── learning.svg
│   ├── env.svg
│   ├── code.svg
│   ├── profile-ascii-1500-topdown-120frames.gif   (animation, 1500 x 1500, 120 frames)
│   ├── profile-ascii-1500-static.png              (finished ASCII portrait, input and fallback)
│   └── fonts/            (Roboto Mono: woff2 for the SVGs, ttf for the GIF)
├── scripts/
│   ├── build_assets.py   (regenerates the terminal SVGs; optional)
│   └── generate_ascii_animation.py   (static ASCII portrait -> top-to-bottom GIF)
└── docs/
    └── SETUP.md
```

The snake files are not in this tree on purpose. The workflow creates them on a separate `output` branch.

## Publish

1. Unzip and copy everything inside the folder into the repository root, including the hidden `.github` folder.
2. Commit and push to the default branch (`main`).
3. Open the **Actions** tab. If GitHub asks, click **I understand my workflows, enable them**.
4. Select **Snake** in the left list, click **Run workflow**, then **Run workflow** again.
5. Wait for the green check (about one minute), then confirm the `output` branch exists with two files.
6. Open your profile and hard refresh (Ctrl+Shift+R). Raw files can be cached for a few minutes.

If Actions → General → Workflow permissions is set to read-only and the run still fails with a 403, choose **Read and write permissions** there and re-run.

## Exact URLs used by the README

| Item | URL |
| :-- | :-- |
| Snake, light | `https://raw.githubusercontent.com/Ujwalushettigar/Ujwalushettigar/output/github-contribution-grid-snake.svg` |
| Snake, dark | `https://raw.githubusercontent.com/Ujwalushettigar/Ujwalushettigar/output/github-contribution-grid-snake-dark.svg` |
| Local assets | `assets/profile-ascii-1500-topdown-120frames.gif`, `assets/profile-ascii-1500-static.png`, `assets/hero.svg`, `assets/boot.svg`, `assets/about.svg`, `assets/architecture.svg`, `assets/learning.svg`, `assets/env.svg`, `assets/code.svg` |
| Activity graph | `github-readme-activity-graph.vercel.app` |
| Stats, streak, languages, pins | `github-readme-stats.vercel.app`, `streak-stats.demolab.com` |
| Tech icons | `skillicons.dev` |

The two snake paths come from the `outputs:` block in `snake.yml`: `dist/<name>.svg` is published to the root of the `output` branch as `<name>.svg`.

## Troubleshooting the snake

If the snake does not appear:

1. GitHub → **Actions**.
2. Open the **Snake** workflow.
3. Click **Run workflow** to run it manually.
4. Check the run status.
5. Open the **output** branch.
6. Confirm both SVG files exist.
7. Open the raw SVG URL from the table above in a browser tab.
8. Refresh the profile.

| Symptom | Cause and fix |
| :-- | :-- |
| Generate step fails with an API or rate-limit error | The workflow passes the default `GITHUB_TOKEN` to snk. Re-run after a few minutes; check that the username in `snake.yml` is spelled exactly `Ujwalushettigar`. |
| Run fails at the publish step with 403 or "Permission denied" | Workflow permissions. The file already sets `contents: write`; also set Settings → Actions → General → Workflow permissions → Read and write. |
| No `output` branch | The publish step did not run or failed. Open the run log, fix the earlier error, re-run. The step creates the branch itself. |
| Branch exists but a file is missing | The generate step failed or the file name changed. Names in `snake.yml` and README must match exactly (including `-dark`). |
| Broken image icon in README | The raw URL is wrong. Open it directly; a 404 means a wrong user, repo, branch or file name. |
| Snake is old or blank | Raw GitHub content is cached for a few minutes. Wait and hard refresh. |
| Workflow never runs | Actions disabled for the repo (enable it in the Actions tab), or no run has been triggered yet. Use Run workflow. |
| Scheduled runs missing | GitHub delays scheduled jobs at busy times and disables schedules after 60 days of no repository activity. Re-enable the workflow and run it manually once. |
| Run works but snake is empty | The account has no public contributions in the last year, or private contributions are hidden in your profile settings. |

## GitHub limitations

- README Markdown cannot change GitHub's page font. Roboto Mono appears only inside the SVG files, where it is embedded.
- GitHub strips JavaScript, `<style>` blocks and hover effects from README HTML, so there are none. All motion is SMIL animation inside SVG images, which GitHub displays reliably. Every SVG's markup is its finished frame and the animation only replays the build-up, so a viewer that ignores animation still sees the complete content.
- Every graphic is drawn at 560 px wide so text stays readable when GitHub scales it to a phone screen.
- SVGs load through GitHub's image proxy, so they cannot fetch anything. The activity graph, stats and icons are separate images from external services; if one of those services is down, only that image fails.
- Images are static pictures to screen readers, so every one has alt text and no information exists only inside an animation.
- The portrait is a GIF, not an SVG, because a GIF animates anywhere an image can be shown and needs no support for SVG animation. GIFs have 256 colours; the portrait is near-monochrome, and the largest colour change from palette rounding is 4 levels out of 255.
- Third-party services (vercel.app, demolab.com) can be rate-limited. The snake and all terminal graphics are served from your own repository.

## ASCII portrait animation

`assets/profile-ascii-1500-static.png` is the finished 1500 x 1500 ASCII portrait (187 x 187 characters). The GIF writes it one line of characters at a time, top to bottom, like a terminal printing the image.

| Frames | What happens | Frame time |
| :-- | :-- | :-- |
| 1 to 96 | rows appear from the top row to the bottom row; finished rows stay; a small cursor block sits on the next row | 50 ms |
| 97 to 110 | the finished portrait is held; the cursor block breathes in and out | 150 ms |
| 111 to 120 | the screen is cleared top to bottom, so the loop restarts from a blank terminal | 50 ms |

Total 120 frames, 7.4 seconds per loop, forever. Every frame differs from the previous one, because GIF writers silently merge identical neighbouring frames.

Regenerate (after changing the PNG, or the timing constants at the top of the script):

```
pip install pillow numpy
python3 scripts/generate_ascii_animation.py
```

The script prints what it verified: 1500 x 1500, exactly 120 frames (counted by Pillow and again by walking the raw GIF blocks), loop forever, every decoded frame identical to the intended frame, and the total duration. It exits with an error if any check fails. Preview locally by dragging the GIF into a browser tab.

To build a new portrait from a photo (the default mode only animates the existing PNG):

```
python3 scripts/generate_ascii_animation.py --photo assets/profile-source.jpg --write-static
```

This converts the photo with a real brightness-to-character mapping (` .:-=+*#%@`, brighter = denser) using Roboto Mono, writes it over the static PNG and animates it. The glyphs will not be pixel-identical to the current PNG, so keep the default mode if you like the current look. The photo is only read, never modified. Tuning constants (`BLACK_POINT`, `GAMMA`, `FOCUS_X`, `FOCUS_Y`) are at the top of the script.

The README uses `<picture>`: visitors whose system asks for reduced motion get the static PNG, everyone else gets the GIF.

## Rebuilding the terminal graphics

```
python3 scripts/build_assets.py
```

This rewrites the SVGs in `assets/`. It needs only Python 3 and the font files in `assets/fonts/`.

## Verification checklist

- [ ] Repository is named `Ujwalushettigar` and is public
- [ ] `.github/workflows/snake.yml` is on the default branch
- [ ] Workflow has `permissions: contents: write`
- [ ] `workflow_dispatch` and a valid `schedule` are present
- [ ] Manual run finishes green
- [ ] `output` branch contains `github-contribution-grid-snake.svg` and `github-contribution-grid-snake-dark.svg`
- [ ] Both raw URLs open in a browser
- [ ] README renders on desktop, in light mode and dark mode, and on mobile
- [ ] Contribution graph, stats, streak and language cards load
