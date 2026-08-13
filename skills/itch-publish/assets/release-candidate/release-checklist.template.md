# Release Candidate Checklist

Status: `LOCAL CANDIDATE — NOT UPLOADED / PRIVATE / PUBLIC RESTRICTED / PUBLIC`

## Product truth

- [ ] Counts match the buyer ZIP
- [ ] Product specification is complete
- [ ] Included and not-included content is explicit
- [ ] License and third-party rights are confirmed
- [ ] AI Disclosure is accurate

## Upload files

- [ ] Versioned filenames
- [ ] Build command/minimal script, staging layout and exclusion rules saved in evidence
- [ ] `build-evidence.md` records each upload, fresh extraction and representative QA
- [ ] README and LICENSE at a visible root
- [ ] No caches, logs, secrets, or unrelated history
- [ ] `unzip -t` passes for every ZIP
- [ ] Every ZIP was extracted into a fresh directory and inspected
- [ ] Free/full/source/Godot access boundaries match the page

## Asset QA

- [ ] Representative files open correctly
- [ ] Dimensions, alpha, origin, frame order and FPS verified
- [ ] Tile/layer/collision rules verified where applicable
- [ ] Godot import and entry demo run in the stated version/renderer, or `N/A — no Godot package`
- [ ] Visual claims verified in a real visible runtime where required

## Page

- [ ] 630×500 cover at 315:250 ratio
- [ ] 8–10 distinct primary previews, excluding the cover
- [ ] All eight mandatory preview roles are represented; optional roles add at most two
- [ ] Every preview has a unique purpose; no crop/recolor padding
- [ ] Cover and 8–10 preview files exist under `page/previews/` and open correctly
- [ ] Preview files come from delivered assets and match page references/captions
- [ ] Actual animation GIF/video where relevant
- [ ] Short description works in listing view
- [ ] First screen states the asset view/genre and type
- [ ] Page says formats, specs, engine versions, license and limitations
- [ ] Preview content is included or clearly labeled otherwise
- [ ] Exactly 10 relevant tags are selected from actual itch.io dropdown candidates; no custom tag was created
- [ ] Saved page was reloaded and all 10 platform tags were read back
- [ ] Mobile-width and logged-out page checks complete

## Publication boundary

- [ ] User approved price
- [ ] User approved final page and uploads
- [ ] Private/Public Restricted preview reviewed
- [ ] Explicit authorization exists before switching to Public

## Evidence and pending items

- Verified:
- Not run:
- Needs user confirmation:
