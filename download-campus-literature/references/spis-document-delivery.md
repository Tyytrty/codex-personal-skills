# Wuhan University of Technology SPIS document delivery

Use the official platform at `https://spis.hnlat.com/`.

## Search

1. Open the platform in the user's authenticated browser.
2. Verify the banner visibly identifies `武汉理工大学`.
3. Enter one DOI in the `请输入关键词/DOI` search box and press `Enter`. Prefer `Enter` because the nearby icon/button may open advanced search.
4. Match the exact title and DOI context in the first relevant result. Do not request a merely similar paper.
5. Click `文献求助` inside that exact result.

## Prepare the request

1. Keep the default `纬度文献互助` route unless the user selects another route.
2. Confirm the displayed title and the prefilled receiving email.
3. Do not copy the receiving email into manifests, logs, or skill files.
4. If the page shows a fee, credit consumption, quota warning, CAPTCHA, or missing contact information, stop and obtain the required user confirmation or input.

## Submit

1. Obtain action-time confirmation that names the papers, destination platform, receiving email, fee status, and required service terms.
2. After confirmation, select the visible service-terms control and verify it is checked.
3. Click `确定` once.
4. Treat modal closure plus return to the matching results page as submission evidence when no persistent success toast is exposed.
5. Record `document_delivery_requested`, platform `spis_hnlat`, and the request date in the manifest. Do not submit the same DOI again.

## After delivery

### QQ Mail to SPIS delivery page

1. Use the user's authenticated Chrome session. Never use, repeat, log, or store a pasted QQ authorization code, mailbox session ID, signed delivery URL, or receiving address.
2. Locate the success email by exact paper title. Read only a bounded DOM excerpt around that title; do not dump the inbox.
3. Open the matching email and click the unique `点击下载` link once.
4. If QQ shows `将要访问外部网页`, click `继续访问` only when the user has explicitly approved that specific external-link step. This is a confirmation step, not permission to bypass a publisher or browser security control.
5. The new tab may go directly to the delivery page when the user's Chrome rule already permits it. Do not require the QQ warning when it does not appear.
6. On the delivery page, verify the exact title and validity period, then click the unique `下载全文` link once.
7. Inspect the user's Downloads folder by modification time. Treat only a completed PDF as success; a new tab, `.crdownload`, or browser notification is not sufficient evidence.

Use browser locators supported by the active browser skill. Take a fresh DOM snapshot before each new page action, require a unique match, and avoid repeated clicks. If `点击下载` appears in both the mail list and opened message, scope to the opened message or to the exact selected `span.mail-subject` item before continuing.

### Recovery and low-token rules

- If an existing QQ Mail tab repeatedly times out, stop retrying that tab. Open a fresh Chrome tab to the stable QQ Mail home page and reuse the existing signed-in session; do not copy a session-bearing inbox URL into logs or manifests.
- If a normal `下载全文` click leaves only `未确认 *.crdownload`, do not click repeatedly. Recheck after a short delay. If the browser skill exposes a supported download method for that same visible link, use it once; otherwise hand off the native Chrome `保留` or `在 Chrome 的 PDF 查看器中打开` action to the user.
- Never automate around Chrome, QQ, CAPTCHA, publisher, or network security checks. Ask for the user's action when a native browser prompt cannot be controlled safely.
- Leave incomplete `.crdownload` files untouched unless the user authorizes cleanup.
- After all browser downloads, switch back to deterministic processing. Use `scripts/reconcile_downloads.py` when a manifest or browser queue is available; otherwise identify the paper from its title or PDF metadata, validate it, and move it to the output directory with the standardized numbered filename.
- Finalize browser tabs after all browser work. Close agent-created QQ warning and delivery tabs; release the user's original mail tab unless it must remain as a handoff.

### Validate and close the request

1. Run `scripts/verify_pdfs.py OUTPUT_DIR`.
2. Require `%PDF-`, size over 10 KB, successful `pypdf` parsing, and a plausible page count.
3. Rename the accepted file using the bibliography number, DOI, and a short title.
4. Change the manifest row to:
   - `status=downloaded`
   - `source=spis_document_delivery`
   - `landing_url=https://spis.hnlat.com/`
   - an absolute standardized file path
   - a note such as `spis_hnlat_delivered_YYYY-MM-DD:<pages>_pages`
5. Keep `candidate_url` empty and never store the expiring email or file-download URL.
6. Report the downloaded filenames, page counts, validation summary, and output directory.
