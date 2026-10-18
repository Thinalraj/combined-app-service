# NUC Workflow 03 — detection-first customer interface

Apply AFTER thinal_nuc_workflow_02.patch. The supplied NUC ZIP is FINISH-01;
it does not already contain Workflow 02. This is an incremental patch, not a
replacement repository. No .pt, .joblib, runtime.json, ROI, price source,
teaching data or calibration file is replaced.

## Apply on your PC

Save both patches in your Windows Downloads folder. Stop this copy's services
and kiosk before applying. Run PowerShell in the repository:

```powershell
cd "D:\project\combined-app-service-latest"
git branch --show-current
git status --short

$p02 = Join-Path $env:USERPROFILE "Downloads\thinal_nuc_workflow_02.patch"
$p03 = Join-Path $env:USERPROFILE "Downloads\thinal_nuc_workflow_03.patch"

git apply --ignore-space-change --check $p02
if ($LASTEXITCODE -ne 0) { throw "Workflow 02 check failed. Stop and copy the exact error." }
git apply --ignore-space-change $p02
if ($LASTEXITCODE -ne 0) { throw "Workflow 02 failed. Stop here." }

git apply --ignore-space-change --check $p03
if ($LASTEXITCODE -ne 0) { throw "Workflow 03 check failed. Stop and copy the exact error." }
git apply --ignore-space-change $p03
if ($LASTEXITCODE -ne 0) { throw "Workflow 03 failed. Stop here." }

git diff --stat
```

The branch should be nuc-testing-v1. If Workflow 02 was already applied by
someone else, do not apply it again. Check the code's BUILD in
service/runtime_status.py and apply only 03 after verifying that 02 is present.
The whitespace option accommodates LF/CRLF source copies; it cannot resolve
different code revisions. Never use --reject, --unsafe-paths, reset --hard,
or force checkout to work around a failed check.

The patch was checked against the previously supplied FINISH-01 branch plus
Workflow 02, and against the uploaded NUC ZIP with both patches in sequence.
Stop if your PC has additional edits overlapping either patch.

## What changed

1. **Detection first:** Place Object becomes Automatic detection. Its large
   green action uses a stable automatic Coin/Bar detection and goes straight
   to mass. The smaller manual correction button opens the existing shape
   chooser. Nothing silently bypasses the backend confidence/shape checks.
2. **Camera lifetime:** Customer camera runs at placement and on the final
   removal screen. No live preview runs on dimensions or frequency acquisition.
   Metrology still captures the necessary frames internally after mass.
3. **Automatic photograph:** Use detected item saves its fresh detection frame
   before mass; manual selection saves a raw placement photo. No customer Snap
   button is shown. Engineering retains manual Snap. Final verification reuses
   that photograph and performs separate fresh inference before the sweep.
   Raw JPEG and HTML/JSON annotations remain separate. The placement photograph
   does not prove that an item stayed unchanged throughout the measurement.
4. **Final screen:** Small removal preview and physical-empty checkbox sit side
   by side, with no vertical scrolling at the normal 800x480 kiosk size. Long
   result, geometry, density and internal-check details are in Details. A
   history read no longer delays showing the result screen.
5. **Removal:** Ticking the physical check remains possible when sensors fail.
   Another Item first uses sensor proof if available; otherwise an explicit
   popup asks whether to continue using visual confirmation. This sends no
   zero/internal operation. A failed final sensor request cannot wait forever.
   Home returns home without claiming that the pan was proven empty.
6. **Preparation:** Customer Start/Another Item adopts a previously verified
   zero if available, otherwise proceeds without declaring zero verified. No
   internal test/adjustment/zero starts automatically in the customer loop.
   Engineering still prepares the empty pan once after startup or movement.
   An already running preparation keeps its empty-pan gate. A spinner follows
   actual preparation status, not a fake delay. Density remains unavailable
   when zero evidence is unavailable. Do not operate TST3/C3/Z with an item on
   the pan; software cannot remove that physical requirement.
7. **Coin/bangle confusion:** OpenCV checks for a large central visible hole
   in a coin prediction. At a conservative 12% interior-area threshold it
   requests manual review as UNKNOWN. It preserves the original YOLO mask and
   its measured area. It is a heuristic, not a trained bangle detector. Bright
   reflections can cause false vetoes; textured support or an invisible hole
   can cause misses. The coin/bar model cannot identify every other shape.
8. **Messages:** Geometry/weight/camera failures and result warnings use bounded
   popups. Repeated placement camera failures are deduplicated for that cycle.
   Normal detection/no-object/multiple-object states remain brief live labels.
   Final removal camera failures remain non-blocking so visual confirmation
   stays usable. Engineering technical readouts remain available.
9. **Home carousel:** Previous/Next and keyboard left/right select all seven
   cached metal quotes; bullion graphics move gently. No vertical prices list.
   Arrows make no API calls. Manual Refresh, server midnight-MYT update,
   stale markers, source configuration and rate limits are unchanged.
10. **Exit:** start_all.bat and launch_chrome.bat use launch_kiosk.py. It owns
    one unique-profile Chrome instance. Exit uses a local, same-origin,
    random-token request and closes only that browser tree. Backends continue
    running. No broad Chrome/Python kill. For an ordinary browser or a remote
    HMI tab, close with Alt+F4. Restart the kiosk with the new launcher before
    testing Exit; an old kiosk has no new launch token. An OS lock prevents
    duplicate supervisors and survives stale JSON after a power interruption.

## NUC smoke test

1. Close the old services and Chrome. Preserve runtime.json's COM11 setting
   and the working ROI. Start normally with start_all.bat. Check /api/status
   reports NUC-03 from the expected folder.
2. Engineering > Load Cell: with the entire pan empty, perform the once-per-
   startup preparation. Internal Auto remains a supported test, not an
   implicit adjustment. The spinner should show while the real job runs.
3. Start Verification: one Coin or Bar, wait for stable detection, use the
   green action. There should be no shape chooser in this automatic path.
   A photo is saved automatically. No user Snap button is displayed.
4. Move/no item/multiple items: automatic action stays disabled. Use manual
   correction deliberately. Manual selection never certifies gold or bypasses
   the reference's minimum 90% vision AND 90% reference-score conditions.
5. Check a bangle against the new hole veto. If missed, retain that example
   for future training; do not assume a colour rule establishes its identity.
6. After mass, verify no live preview during dimensions/sweep. Geometry may
   still take several real measurement frames. Missing depth can use known
   manual thickness as before; missing zero keeps density unavailable.
7. Review Details, remove the item, tick the physical-empty checkbox and
   Another Item. If sensors fail, confirm the explicit visual-only popup.
   No repeated TST3/C3/Z should occur. Test Cancel in that popup too.
8. Simulate an unavailable camera/weight service. Errors should be actionable
   and result navigation should remain usable. Check all actions fit at the
   actual NUC display scale; unusually high OS/browser zoom can still need
   adjustment. Engineering screens retain scrolling for technical content.
9. Home: try all seven cards and Refresh. Exit should close kiosk Chrome and
   leave the four backend consoles running. launch_chrome.bat reopens it.

The 916/999 reference score remains uncalibrated research evidence. A strong
score or plausible density does not establish gold identity or actual purity.
Warnings are preserved in saved records and Details, not discarded.

## Commit and transfer

After checking the diff on your PC, stage tracked edits plus the new source
files below. Do not stage generated photo/data folders or Python caches:

```powershell
git add -u
git add -- service/acceptance_policy.py service/image-service/geometry_live.py system_assets/NUC_02_FIX_GUIDE.md service/image-service/coin_hole_guard.py service/kiosk_control.py launch_kiosk.py system_assets/NUC_03_FIX_GUIDE.md
git diff --cached --stat
git commit -m "Apply NUC workflow 02 and detection-first UI 03"
git push origin nuc-testing-v1
```

On the NUC, stop the old stack, open its repo and run git status first. If it
has uncommitted hardware fixes, preserve/commit them before pulling. Do not
reset them away. With a clean branch:

```powershell
cd "C:\Users\NUC\Documents\combined-app-service-nuc-test"
git switch nuc-testing-v1
git pull --ff-only origin nuc-testing-v1
.\start_all.bat
```

If Git reports overlapping local modifications or a divergent branch, stop
and retain the exact message. Keep the local COM11/ROI/configuration intact.

## Validation and files

Changed: app.js, index.html, styles.css, app.py, yolo_preview.py,
runtime_status.py, launch_stack.py, launch_chrome.bat.
New: launch_kiosk.py, service/kiosk_control.py,
service/image-service/coin_hole_guard.py and this guide.

Python/JavaScript syntax and HTML ID checks passed. Controlled tests exercised
real OpenCV hole/solid/glint examples and Segmenter acceptance, Flask snapshot
reuse plus fresh low-confidence rejection, local/token-scoped kiosk Exit,
specific owned-PID termination, UI manual removal, preparation reuse, active-
preparation guard, capture cancellation, carousel wrapping and spinner state.
No physical balance, RealSense stream, actual model accuracy, Windows Chrome
process lifecycle or rendered NUC screen was tested in this environment.
