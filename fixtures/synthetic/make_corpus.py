#!/usr/bin/env python3
"""make_corpus.py - D5: a synthetic agent memory with planted rot and ground truth.

Everything here is fiction: a made-up bookbinding studio, its owner, insurer, clients,
assistant, van and cat. No real note, person, company, date or path from any real corpus
is used. The corpus exists so the memory-rot tools can be demonstrated and calibrated
without showing one real note.

Written under fixtures/synthetic/seed<N>/ (one folder per seed, re-runs overwrite in place,
nothing is ever deleted):
  memory/             57 notes + MEMORY.md index; file mtimes set deterministically
  fs/                 a tiny sandbox filesystem the notes point at (real files for live
                      paths; deliberately missing files for dead paths)
  session/            transcript.jsonl (the parked session), HANDOFF_<date>.md (its
                      hand-style handoff), successor_first_turn.md (the next session's
                      first human turn = the survival ground truth)
  ground_truth.json   every planted signal, the trap, and the rubric answers with match keys
  audit_check.json    (--verify) the read-only audit.py run on the corpus, anchor date

Planted, per the D5 design: 8 passed horizons (one of them the trap), 6 absence claims each
resolved in a newer sibling note, 5 dead paths, 4 dangling links, 6 stamp drifts, 9 negatives
that must NOT flag (3 remote-host paths, 3 dock-only fold paths, 3 modeling-input dates),
12 clean controls, 6 resolver notes and the trap's sibling.

Usage:
  python3 -I make_corpus.py --seed 1 [--out DIR] [--verify]
"""
import argparse, datetime as dt, json, os, random, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent.parent
AUDIT = SKILL / "scripts" / "audit.py"
ANCHOR = dt.date(2026, 10, 31)        # the successor session's "today"
SESSION_DATE = dt.date(2026, 8, 28)   # the parked session

WORLDS = [
    dict(owner="Noor Haddad", owner_first="Noor", studio="Kestrel Bindery", slug="kestrel", city="Asheville",
         insurer="Piedmont Mutual", insurer_key="piedmont", agent="Rosa Entwistle", agent_last="entwistle",
         client="Okonkwo-Reyes", client_slug="okonkwo_reyes", client_key="okonkwo",
         assistant="Dani", assistant_key="dani", host="Squarespace", host_key="squarespace", current_host="Hostwell",
         cat="Mortise", cat_key="mortise", van="the Transit", venue="Burnside Hall", venue_key="burnside",
         grant="Blue Ridge Craft Grant", supplier="Fennimore Mills", supplier_key="fennimore",
         appraiser="Highland Appraisals", policy="KB-2231", serial="C193-8827", ref="PM-44817", plate="KBD-4471",
         apprentice="Mira Castellanos", college="Warren Wilson", phone="(828) 555-0142", wifi="KestrelStudio-5G"),
    dict(owner="Teodora Vasquez", owner_first="Teodora", studio="Harrow & Thread Bindery", slug="harrow", city="Duluth",
         insurer="Lakeshore Mutual", insurer_key="lakeshore", agent="Ivan Petrosyan", agent_last="petrosyan",
         client="Lindqvist-Abara", client_slug="lindqvist_abara", client_key="lindqvist",
         assistant="Priya", assistant_key="priya", host="Wix", host_key="wix", current_host="Northpoint Hosting",
         cat="Quire", cat_key="quire", van="the Sprinter", venue="Canal Park Annex", venue_key="canal park",
         grant="Arrowhead Makers Grant", supplier="Birchbark Paper Co.", supplier_key="birchbark",
         appraiser="Superior Appraisal Group", policy="HT-7740", serial="C193-5510", ref="LM-20991", plate="HTB-2208",
         apprentice="Jonah Ekwueme", college="Lake Superior College", phone="(218) 555-0177", wifi="HarrowStudio-5G"),
    dict(owner="Ilse Marchetti", owner_first="Ilse", studio="Lantern Press Bindery", slug="lantern", city="Olympia",
         insurer="Cascade Assurance", insurer_key="cascade", agent="Marcus Oyelaran", agent_last="oyelaran",
         client="Brennan-Sato", client_slug="brennan_sato", client_key="brennan",
         assistant="Teo", assistant_key="teo", host="Webflow", host_key="webflow", current_host="Evergreen Host",
         cat="Folio", cat_key="folio", van="the Promaster", venue="Capitol Annex", venue_key="capitol",
         grant="Puget Craft Fund", supplier="Nisqually Paper Works", supplier_key="nisqually",
         appraiser="Sound Appraisals", policy="LP-1188", serial="C193-3304", ref="CA-58203", plate="LPB-9032",
         apprentice="Rosa Delacroix", college="Evergreen State", phone="(360) 555-0119", wifi="LanternStudio-5G"),
]

def D(m, d, y=2026): return dt.date(y, m, d)
def fm_stamp(d): return f"{d.isoformat()}T14:00:00.000Z"
def mtime_ts(d): return time.mktime(dt.datetime(d.year, d.month, d.day, 14, 0, 0).timetuple())

class Corpus:
    def __init__(self, W):
        self.W = W; self.notes = []
    def add(self, file, desc, type_, mtime, body, kind, should_flag, expect, why, stamp=None, append=None):
        W = self.W
        file = file.format(**W); desc = desc.format(**W); body = body.format(**W).strip() + "\n"
        if append: body += "\n" + append.format(**W) + "\n"
        self.notes.append(dict(file=file, name=file[:-3], desc=desc, type=type_, mtime=mtime, stamp=stamp or mtime,
                               body=body, kind=kind, should_flag=should_flag, expect=expect, why=why))

def build(W, rng):
    c = Corpus(W)
    fs = W["fs"]
    # ---- H: 8 passed horizons (note edited BEFORE a date it points at; the date is before the anchor) ----
    c.add("{slug}_equipment_policy.md",
          "Equipment policy rider on the guillotine cutter: appraisal must reach {insurer} by 9/7/2026 or the rider coverage ends",
          "project", D(8, 20),
          "Policy {policy} with {insurer}; agent {agent} (direct line in the studio phone). The rider on the guillotine cutter "
          "(Challenge 193, serial {serial}) requires a current appraisal on file by 2026-09-07 or the rider coverage ends and the "
          "cutter is insured at scrap value only. {appraiser} is booked for 8/31 at 10:00 AM. After the appraisal: email the PDF to "
          "{agent} and confirm receipt before 9/7. Premium unchanged at $148/month through the 2027 renewal.",
          "horizon", True, {"horizon": 1}, "THE TRAP: the 9/7 deadline was mooted on 9/10 in a sibling note; this note never changed")
    c.add("{slug}_van_registration.md", "Van registration expires 9/30/2026; renew on the county portal", "project", D(8, 12),
          "Registration on {van} (plate {plate}) expires 2026-09-30; renew on the county portal. Emissions test done 8/9, cert in the "
          "glovebox. Renewal fee $86. The owner does this one herself.",
          "horizon", True, {"horizon": 1}, "renewal date passed after the last edit")
    c.add("{slug}_grant_application.md", "{grant} application submitted 8/3/2026; decisions mailed by 10/15", "project", D(8, 4),
          "{grant} application submitted 2026-08-03 for the board shear ($6,000). Decisions are mailed by 2026-10-15. Contact: grants "
          "office, ext. 204. If awarded, order the Challenge 30-inch shear the same week.",
          "horizon", True, {"horizon": 1}, "decision date passed; outcome never recorded")
    c.add("fall_workshop_venue.md", "{venue} holds the Thursday evening workshop dates until 9/15/2026; $300 deposit with the hold form", "project", D(8, 22),
          "{venue} holds the Thursday evening dates (Oct 8, Oct 15, Oct 22, Oct 29, 6:00-8:30 PM) until 2026-09-15. Deposit $300 due "
          "with the signed hold form; capacity 14; tables included; we bring the presses.",
          "horizon", True, {"horizon": 1}, "hold expiry and the session dates all passed after the last edit")
    c.add("library_archive_commission.md", "County library archive rebinding: samples due 8/20, delivery 10/1/2026", "project", D(7, 30),
          "County library archive rebinding, 14 volumes, quarter leather. Samples due 2026-08-20; full delivery 2026-10-01; invoice net "
          "30 after delivery. Contact: special collections desk.",
          "horizon", True, {"horizon": 2}, "both milestones passed; nothing recorded since July")
    c.add("paper_order_{supplier_key}.md", "{supplier} order: 40 reams, ships 9/4, expected 9/11/2026", "project", D(8, 15),
          "Order 20417 with {supplier}: 40 reams Superfine cover, ships 2026-09-04, expected 2026-09-11, freight prepaid. Check the "
          "moisture wrap on arrival and photograph any dented cartons before signing.",
          "horizon", True, {"horizon": 2}, "ship and arrival dates passed; receipt never recorded")
    c.add("cat_{cat_key}_vet.md", "{cat}'s rabies booster due 9/20/2026 at Riverbend Vet", "reference", D(8, 6),
          "{cat} (studio cat): rabies booster due 2026-09-20 at Riverbend Vet (Dr. Amsel). Weight 11.2 lb on 8/5. Carrier is under "
          "the sewing frame.",
          "horizon", True, {"horizon": 1}, "booster date passed")
    c.add("quarterly_tax_q3.md", "Q3 estimated tax due 9/15/2026: $1,340 federal + $410 state", "project", D(8, 18),
          "Q3 estimated tax payment due 2026-09-15: $1,340 federal + $410 state, paid through the bookkeeper portal. Receipts go in "
          "the finances folder.",
          "horizon", True, {"horizon": 1}, "due date passed; payment never recorded")
    # ---- A: 6 absence claims, each resolved later in a different (sibling) note ----
    c.add("{slug}_hvac_landlord.md", "Landlord has not replied to the 7/15 HVAC letter; waiting on a written commitment", "project", D(7, 28),
          "Greer Properties has not replied to the 7/15 letter about the HVAC repair; no reply as of 7/28. Waiting on a written "
          "commitment before paying August rent in full. Unit struggles above 82F.",
          "absence", True, {"absence": 1}, "resolved 9/16 in the lease-renewal note; this note still says no reply")
    c.add("apprentice_inquiry.md", "{college} student asked about a fall apprenticeship; terms sent 7/8; awaiting a reply", "project", D(7, 10),
          "A {college} bookbinding student asked about a fall apprenticeship. Sent the terms 7/8 (Mondays, $18/hr stipend). "
          "Awaiting a reply; unverified whether their program allows credit.",
          "absence", True, {"absence": 2}, "superseded 9/25 in the fall-staffing note: a different apprentice accepted")
    c.add("domain_renewal_dispute.md", "Registrar charged twice for the domain renewal; refund request 4471 open, no response", "project", D(7, 22),
          "Registrar charged twice for the .studio domain renewal on 6/30. Refund request 4471 opened 7/2; no response yet; pending "
          "with their billing team. Amount $18.40.",
          "absence", True, {"absence": 2}, "refund landed 8/29, recorded in the card-statement note only")
    c.add("bookfair_booth_application.md", "Applied for a booth at the {city} Book & Paper Fair; no confirmation yet", "project", D(8, 1),
          "Applied 7/20 for a booth at the {city} Book & Paper Fair (Nov 14-15). No confirmation yet; waiting on the organizers' "
          "lottery. Booth fee $220 if drawn.",
          "absence", True, {"absence": 2}, "booth confirmed 8/16, recorded in the fair-logistics note only")
    c.add("glue_supplier_sample.md", "Asked Pelican Adhesives for a PVA sample; never arrived; still open", "project", D(7, 18),
          "Asked Pelican Adhesives for a PVA sample on 7/12. Never arrived; still open. Will re-order from the usual supplier if "
          "nothing shows in two weeks.",
          "absence", True, {"absence": 2}, "sample arrived 7/24, recorded in the adhesives-inventory note only")
    c.add("press_rental_quote.md", "Quote requested from Iron Hand Presses for a Vandercook rental; no reply; outcome unknown", "project", D(8, 9),
          "Quote requested 8/2 from Iron Hand Presses for a six-month Vandercook SP-15 rental. No reply; outcome unknown. Budget "
          "cap $900/month.",
          "absence", True, {"absence": 2}, "Iron Hand replied 8/20; rental booked; recorded in the letterpress-plan note only")
    # ---- R: the 6 resolver notes (newer, true) + the trap's sibling ----
    c.add("{slug}_lease_renewal.md", "Studio lease renewed through 7/31/2028; HVAC repair done 9/19", "project", D(9, 22),
          "Lease at 412 Depot St renewed 9/16 through 2028-07-31 at $1,720/month starting with the October rent. EDIT 2026-09-18: "
          "Greer Properties replied 9/16; the HVAC repair was scheduled and completed 9/19 (invoice on file). The HVAC note is OUT "
          "OF DATE on this; its open item is RETRACTED.",
          "resolver", False, {"flips": 1}, "resolves the HVAC absence")
    c.add("fall_staffing.md", "Fall staffing: {assistant} Tue/Thu only from 10/1; apprentice {apprentice} Mondays from 10/6", "project", D(10, 8),
          "{assistant} works Tue/Thu only from 10/1 (school schedule), $19/hr. EDIT 2026-09-28: the apprentice-inquiry note is "
          "SUPERSEDED. {apprentice} accepted 9/25, starts 10/6, Mondays 9 AM-3 PM, credit approved by her program.",
          "resolver", False, {"flips": 1}, "resolves the apprentice absence; carries the assistant's new schedule")
    c.add("studio_card_statement_aug.md", "August card statement reconciled 9/6; registrar refund landed 8/29", "reference", D(9, 8),
          "August card statement reconciled 9/6: 31 lines, all matched. EDIT 2026-09-06: registrar refund 4471 landed 8/29 ($18.40); "
          "the domain-dispute note is OUT OF DATE; its open item is RETRACTED.",
          "resolver", False, {"flips": 1}, "resolves the domain-dispute absence")
    c.add("fair_logistics_nov.md", "{city} Book & Paper Fair: booth 22 confirmed; load-in 11/13 4:00 PM", "project", D(10, 12),
          "Booth 22 confirmed (email 8/16, lottery drawn). Table and two chairs included; load-in 11/13 at 4:00 PM; bring the "
          "folding shelves. EDIT 2026-08-16: the booth-application note is OUT OF DATE; its open item is RETRACTED.",
          "resolver", False, {"flips": 1}, "resolves the booth absence")
    c.add("adhesives_inventory.md", "Adhesives inventory 9/29: PVA 2 gal, wheat paste 1 lb", "reference", D(9, 30),
          "Inventory 9/29: PVA 2 gal (Pelican sample arrived 7/24 and was fine; ordered 4 gal on 8/3), wheat paste 1 lb, methyl "
          "cellulose 200 g. EDIT 2026-09-29: the glue-sample note is OUT OF DATE; its open item is RETRACTED.",
          "resolver", False, {"flips": 1}, "resolves the glue-sample absence")
    c.add("letterpress_plan_fall.md", "Vandercook SP-15 rental starts 11/2 at $780/month (Iron Hand replied 8/20)", "project", D(10, 5),
          "Vandercook SP-15 rental starts 11/2 for six months at $780/month; Iron Hand Presses replied 8/20. Delivery through the "
          "alley door. EDIT 2026-10-04: the press-rental note is OUT OF DATE; its open item is RETRACTED.",
          "resolver", False, {"flips": 1}, "resolves the press-rental absence")
    c.add("{slug}_finances_q3_2026.md", "Q3 2026 close: revenue $21,400, materials $6,120, net $7,210", "project", D(9, 14),
          "Q3 close: revenue $21,400; materials $6,120; {assistant} payroll $4,980; rent $4,950; net $7,210. EDIT 2026-09-12: the "
          "9/7 appraisal deadline is MOOT. {insurer} extended the cutter rider to 2026-12-31 after the 9/10 call (ref {ref}); the "
          "appraisal is on file as of 9/10. Do not re-send it. The equipment-policy note still says 9/7 and is WRONG.",
          "trap_sibling", False, {"flips": 1}, "the retraction the trap note never received")
    # ---- DP: 5 dead paths (the parent folder exists in fs/, the named file or folder does not) ----
    c.add("pricing_sheet.md", "Current pricing sheet location", "reference", D(9, 2),
          "Current pricing lives in {fs}/archive/2025_pricing.xlsx; update the album tiers there before quoting.",
          "deadpath", True, {"dead": 1}, "the sheet moved to the NAS in June; the path is dead")
    c.add("scan_workflow.md", "Album proof scans: 600 dpi TIFF to the album_proofs folder", "reference", D(8, 30),
          "Album proof scans go to {fs}/scans/album_proofs/ as 600 dpi TIFF; clients get JPEG exports from the same folder.",
          "deadpath", True, {"dead": 1}, "folder never recreated after the laptop rebuild")
    c.add("invoice_generator.md", "Invoices: run invoice_gen.py with the order slug", "reference", D(7, 26),
          "Invoices: run {fs}/tools/invoice_gen.py with the order slug; templates in {fs}/templates/.",
          "deadpath", True, {"dead": 1}, "the script was never restored; templates folder is live")
    c.add("backup_drive_rotation.md", "Weekly backup to the orange drive, monthly to the NAS", "reference", D(8, 14),
          "Weekly backup to {fs}/backups/weekly/ (the orange drive), monthly to the NAS. Last full on 8/9.",
          "deadpath", True, {"dead": 1}, "weekly folder does not exist")
    c.add("label_printer_setup.md", "Label printer profile and reinstall steps", "reference", D(9, 5),
          "Label printer profile at {fs}/config/labelwriter.plist; reinstall from {fs}/config/ if labels print blank.",
          "deadpath", True, {"dead": 1}, "plist missing; config folder is live")
    # ---- DL: 4 dangling wikilinks ----
    c.add("grant_budget_notes.md", "Grant budget lines; board shear quote $5,400", "project", D(9, 12),
          "Budget lines for the grant: see [[grant-budget-worksheet]] for the line items. Board shear quote $5,400 from Challenge; "
          "freight $240.",
          "dangling", True, {"dangling": 1}, "the worksheet note was never written")
    c.add("workshop_curriculum.md", "Thursday series: pamphlet stitch, coptic, case binding", "reference", D(9, 20),
          "Thursday series: pamphlet stitch, then coptic, then case binding. Materials list in [[workshop-materials-list]]; handouts "
          "printed in-house.",
          "dangling", True, {"dangling": 1}, "materials list note missing")
    c.add("holiday_closure_plan.md", "Closed 12/24 to 1/2; see the order-cutoff note", "reference", D(9, 25),
          "Closed 12/24 through 1/2. Sign on the door, voicemail updated. See [[holiday-order-cutoffs]] for the last ship dates.",
          "dangling", True, {"dangling": 1}, "cutoffs note missing")
    c.add("tool_sharpening.md", "Knives and bone folders sharpened quarterly by Ridgeline Edge", "reference", D(10, 1),
          "Bone folders and knives sharpened quarterly by Ridgeline Edge; last done 9/28. Log in [[sharpening-log]].",
          "dangling", True, {"dangling": 1}, "log note missing")
    # ---- SD: 6 stamp drifts (frontmatter stamp older than the real mtime: a scripted append moved the file) ----
    sd = [("thread_and_cord_inventory.md", "Linen thread and cord inventory; reorder at 4 spools", D(10, 20), D(9, 1),
           "Linen thread 18/3 x12 spools, 25/3 x8; cord for sewn boards 40 m. Reorder at 4 spools.", "[[adhesives-inventory]]"),
          ("open_studio_hours.md", "Open studio: Wed 2-6 PM, Sat 10 AM-2 PM", D(10, 18), D(8, 30),
           "Open studio: Wed 2:00-6:00 PM, Sat 10:00 AM-2:00 PM. Sign-up sheet by the door; cap 6.", "[[thursday-workshop-roster]]"),
          ("board_shear_wishlist.md", "Board shear: Challenge 30-inch, budget $5,400", D(10, 24), D(9, 15),
           "Board shear: Challenge 30-inch preferred; budget $5,400; decide after the grant letter.", "[[grant-budget-notes]]"),
          ("client_intake_form.md", "Intake form fields", D(10, 21), D(9, 3),
           "Intake form fields: project, volumes, page count, cover material, deadline, budget band, how they found us.", "[[quote-template-location]]"),
          ("van_maintenance_log.md", "Van maintenance: oil change 8/27 at 61,200 mi", D(10, 26), D(8, 28),
           "Oil change 8/27 at 61,200 mi; tires rotated; next service at 66,000 mi. Wiper blades in the side pocket.", "[[van-parking-permit]]"),
          ("studio_insurance_overview.md", "Policies: general liability, equipment, commercial auto", D(10, 23), D(9, 10),
           "Policies: general liability (renews annually in March), equipment policy (see [[{slug}-equipment-policy]]), commercial "
           "auto on the van.", "[[{slug}-finances-q3-2026]]")]
    for f, desc, mt, st, body, link in sd:
        c.add(f, desc, "reference", mt, body, "stampdrift", False, {"drift": 7},
              "a scripted 'Related:' append moved the mtime; the stamp still says the old date", stamp=st, append="Related: " + link)
    # ---- NEG: 9 that must NOT flag (they do under the current audit.py: the three known D6 defects) ----
    c.add("nas_archive_layout.md", "Client archives live on the studio NAS, not the laptop", "reference", D(9, 16),
          "The studio NAS (host ridge-nas, SMB) keeps client archives at /Users/Shared/{slug}-archive/ on the NAS itself. Mount it "
          "before searching; nothing in it is on this laptop.",
          "neg_remote", False, {"fp": "dead"}, "remote-host path looks local to the tool")
    c.add("print_shop_dropbox.md", "Ridgeline Print receives files over sftp on their Mac mini", "reference", D(9, 18),
          "Ridgeline Print receives files at /Users/ridgeline/ on THEIR Mac mini, over sftp. Not a local folder.",
          "neg_remote", False, {"fp": "dead"}, "remote-host path looks local to the tool")
    c.add("assistant_laptop_templates.md", "{assistant}'s studio laptop keeps the label templates", "reference", D(9, 24),
          "{assistant}'s studio laptop keeps the label templates at /Users/{assistant_key}/ on her machine, not this one.",
          "neg_remote", False, {"fp": "dead"}, "remote-host path looks local to the tool")
    c.add("scanner_dock_volumes.md", "Scanner dock mounts BENCH-B only while attached", "reference", D(9, 19),
          "With the scanner dock attached, scans land in ~/Desktop/BENCH-B/ (a mounted volume). The folder is absent when undocked "
          "by design, not because anything is missing.",
          "neg_fold", False, {"fp": "dead"}, "dock-only volume reads as a dead path")
    c.add("card_reader_mount.md", "Camera card mounts BENCH-C while inserted", "reference", D(9, 21),
          "The camera card mounts at ~/Desktop/BENCH-C/ only while the card is in the reader.",
          "neg_fold", False, {"fp": "dead"}, "dock-only volume reads as a dead path")
    c.add("dock_export_folder.md", "Dock export queue BENCH-D exists only while docked", "reference", D(9, 27),
          "Dock export queue: ~/Desktop/BENCH-D/ exists only while docked; the print queue drains it.",
          "neg_fold", False, {"fp": "dead"}, "dock-only volume reads as a dead path")
    c.add("cash_model_assumptions.md", "Cash model inputs: month one, materials rise", "reference", D(8, 5),
          "Cash model assumes 2026-09-01 as month one and a 3% materials rise from 2026-10-01. These are inputs to the model, not "
          "events that happen.",
          "neg_modeling", False, {"fp": "horizon"}, "modeling-input dates look like expectations")
    c.add("pricing_scenario_fall.md", "Pricing scenario: album tier to $1,950", "reference", D(8, 11),
          "Scenario only: if the album tier moves to $1,950 from 2026-09-15, Q4 margin improves 4 points. Modeling input, not a plan.",
          "neg_modeling", False, {"fp": "horizon"}, "modeling-input dates look like expectations")
    c.add("rent_step_model.md", "Lease step-up modeled from 10/1", "reference", D(8, 8),
          "Model the lease step-up as $1,650 to $1,720 from 2026-10-01; the actual lease terms are in the lease note.",
          "neg_modeling", False, {"fp": "horizon"}, "modeling-input dates look like expectations")
    # ---- CTRL: 12 clean controls (fresh, true, nothing to flag) ----
    c.add("{client_slug}_album_order.md", "{client} wedding album set: 3 volumes, accepted 9/9, production starts 11/3", "project", D(9, 10),
          "Wedding album set for the {client} wedding (Nov 7 ceremony): 3 volumes, premium tier. Quote sent 2026-09-02 at $1,850; "
          "ACCEPTED 2026-09-09, deposit $925 received 9/9. Production starts 2026-11-03. Spec at {fs}/orders/{client_slug}_spec.pdf; "
          "quote built from {fs}/templates/quote_template.md.",
          "control", False, {}, "fresh; carries a post-session fact the successor will have to re-state")
    c.add("studio_website_host.md", "Website stays on {current_host}; migration to {host} dropped 8/28", "project", D(8, 28),
          "Site is on {current_host}; DNS at the registrar. Decision 8/28: the migration to {host} is DROPPED. {assistant} renewed "
          "{current_host} for a year on 8/25 ($180), good through 2027-08-25. Site stays where it is.",
          "control", False, {}, "edited during the parked session; true")
    c.add("studio_address_card.md", "{studio}: 412 Depot St, {city}; Tue-Sat 10 AM-5 PM", "reference", D(10, 22),
          "{studio}, 412 Depot St, {city}. Studio line {phone}. Hours Tue-Sat 10:00 AM-5:00 PM; Mondays by appointment.",
          "control", False, {}, "clean")
    c.add("supplier_contacts.md", "Supplier reps: {supplier}, Pelican Adhesives, Ridgeline Print", "reference", D(10, 24),
          "{supplier}: rep Lena Fairweather, orders by email. Pelican Adhesives: rep line, mornings. Ridgeline Print: Marco, "
          "walk-ins fine.",
          "control", False, {}, "clean")
    c.add("quote_template_location.md", "Quote template and order spec folders", "reference", D(10, 25),
          "Quote template: {fs}/templates/quote_template.md. Order specs: {fs}/orders/. Invoice template: "
          "{fs}/templates/invoice_template.md.",
          "control", False, {"live": 3}, "live paths")
    c.add("bookkeeper_portal.md", "Bookkeeper: Fernwood Accounting; monthly statements in the portal", "reference", D(10, 23),
          "Bookkeeper: Fernwood Accounting. Portal login lives in the password manager; statements appear monthly; quarterly "
          "estimates are paid from there.",
          "control", False, {}, "clean")
    c.add("studio_cat_{cat_key}.md", "{cat}: 11.4 lb on 10/26, Riverbend Vet, no meds", "reference", D(10, 27),
          "{cat}: 11.4 lb (10/26). Riverbend Vet. Food in the back cabinet, one scoop twice a day. No meds.",
          "control", False, {}, "clean")
    c.add("thursday_workshop_roster.md", "Fall series roster: 11 of 14 seats filled", "project", D(10, 28),
          "Fall series roster: 11 of 14 seats filled, waitlist 3. Materials fee $45 collected at session one. Name tags in the "
          "tin.",
          "control", False, {}, "clean")
    c.add("van_parking_permit.md", "Depot St loading-zone permit LZ-2291, valid through 3/31/2027", "reference", D(10, 21),
          "Depot St loading-zone permit LZ-2291 on the dash; valid through 2027-03-31; renew at the city clerk.",
          "control", False, {}, "future date only")
    c.add("studio_wifi_and_printer.md", "Wi-Fi and printer addresses", "reference", D(10, 20),
          "Wi-Fi: {wifi}. Printer: Brother on 192.168.4.22. Label printer on USB at the front desk.",
          "control", False, {}, "clean")
    c.add("apprentice_{apprentice_key}_onboarding.md", "{apprentice}: Mondays 9 AM-3 PM from 10/6; stipend $18/hr", "project", D(10, 26),
          "{apprentice}: Mondays 9:00 AM-3:00 PM from 10/6; stipend $18/hr; credit form signed 10/3. See [[fall-staffing]].",
          "control", False, {}, "valid link")
    c.add("materials_reorder_points.md", "Reorder points: bookcloth, board, PVA, thread", "reference", D(10, 29),
          "Reorder points: bookcloth 10 yd, binder's board 20 sheets, PVA 1 gal, thread 4 spools. See "
          "[[thread-and-cord-inventory]].",
          "control", False, {}, "valid link")
    return c

# ---------------------------------------------------------------- the parked session ----
def session_fixture(W, corpus):
    fs = W["fs"]; notes = {n["file"]: n for n in corpus.notes}
    pol = W["slug"] + "_equipment_policy.md"; van = W["slug"] + "_van_registration.md"
    cli = W["client_slug"] + "_album_order.md"; ven = "fall_workshop_venue.md"; web = "studio_website_host.md"
    client_0828 = ("Wedding album set for the {client} wedding (Nov 7 ceremony): 3 volumes, premium tier. Spec at "
                   "{fs}/orders/{client_slug}_spec.pdf; quote to be built from {fs}/templates/quote_template.md and sent to the "
                   "couple by 2026-09-02.").format(**W)
    website_0826 = ("Plan: migrate the site from {current_host} to {host} in September. {current_host} renews 8/25 ($180/yr); "
                    "decide before the renewal. DNS at the registrar.").format(**W)
    handoff_name = f"HANDOFF_2026-08-28_1640_{W['slug']}.md"
    handoff = f"""# HANDOFF 2026-08-28 4:40 PM - {W['studio']}: fall planning

Session: about 50 minutes, five notes loaded (equipment policy, {W['client']} album, van, venue, website). Parked until after fair season.

## WHAT WAS DONE
- Loaded memory/{pol}, memory/{cli}, memory/{van}, memory/{ven}, memory/{web}.
- Website: migration to {W['host']} DROPPED. {W['assistant']} renewed {W['current_host']} for a year on 8/25. Edit appended to the website note. Do not touch the site.
- Album: premium tier, 3 volumes, $1,850, 50% deposit. Template {fs}/templates/quote_template.md; spec {fs}/orders/{W['client_slug']}_spec.pdf.
  {fs}/archive/2025_pricing.xlsx is gone (moved to the NAS); {fs}/scans/album_proofs/ does not exist yet.
- Decided 8/28: {W['assistant']} to $19/hr effective 9/1. Thursday-only workshop series, Saturday dropped (decided 8/27, confirmed 8/28).

## WHAT'S PENDING
1. Send the {W['client']} album quote ($1,850) by 9/2.
2. Appraisal 8/31 at 10:00 AM ({W['appraiser']}); PDF to {W['agent']} at {W['insurer']}; written confirmation on file before 9/7 or the cutter rider ends.
3. Van registration renewal by 9/30 (owner does the county portal).
4. Venue: signed hold form and $300 deposit to {W['venue']} before 9/15 (Thursday dates Oct 8-29).

## NEXT ACTION
Morning of 9/1: call {W['agent']} at {W['insurer']}, send the appraisal PDF, get written confirmation it is on file before 9/7.

## RESUMPTION PROMPT
Pick up {W['studio']} fall planning from this handoff. Work the four pending items in order; the insurer confirmation comes first.
"""
    T = lambda h, m: f"2026-08-28T{h:02d}:{m:02d}:00"
    ev = []
    def U(h, m, text): ev.append(dict(t=T(h, m), role="user", content=text))
    def A(h, m, text): ev.append(dict(t=T(h, m), role="assistant", content=text))
    def TOOL(h, m, name, inp, result): ev.append(dict(t=T(h, m), role="tool", tool=name, input=inp, result=result))
    U(15, 50, f"Fall planning for {W['studio']}. Load what we have on the equipment rider, the {W['client']} album, the van, the fall "
              "workshop venue and the website, then help me sort out what is due in the next two weeks.")
    A(15, 50, "Reading the five notes.")
    for f, body in [(pol, notes[pol]["body"]), (cli, client_0828), (van, notes[van]["body"]), (ven, notes[ven]["body"]), (web, website_0826)]:
        TOOL(15, 51, "Read", {"file_path": f"memory/{f}"}, body.strip())
    A(15, 53, f"Due in the next two weeks: the {W['client']} quote by 9/2; the cutter appraisal 8/31, then the PDF to {W['insurer']} "
              "with confirmation on file before 9/7 (the rider ends otherwise); the venue hold form and deposit by 9/15; the van "
              f"registration by 9/30. The website note says {W['current_host']} renewed 8/25 and the plan was to decide before then. "
              "Did it renew?")
    U(15, 55, f"{W['assistant']} renewed {W['current_host']} for a year on 8/25, I forgot to tell you. So scratch the migration to "
              f"{W['host']}. Don't touch the site. Note it.")
    A(15, 56, "Noted. Appending the decision to the website note.")
    TOOL(15, 56, "Edit", {"file_path": f"memory/{web}", "append": f"Decision 8/28: the migration to {W['host']} is DROPPED. "
                 f"{W['assistant']} renewed {W['current_host']} for a year on 8/25 ($180), good through 2027-08-25. Site stays where it is."},
         "appended")
    U(15, 58, f"Pricing for the album: premium tier, three volumes. The 2025 sheet is in {fs}/archive/2025_pricing.xlsx I think.")
    TOOL(15, 59, "Glob", {"pattern": f"{fs}/archive/*"}, "(no matches)")
    A(15, 59, f"{fs}/archive/2025_pricing.xlsx is not here; the archive folder is empty and the NAS note says client archives moved "
              f"to the NAS in June. Using the premium tier from {fs}/templates/quote_template.md: $1,850 for three volumes, 50% deposit.")
    U(16, 2, f"Good. Quote at $1,850, send it by Tuesday 9/2. Proofs: scans go to {fs}/scans/album_proofs/ like last time?")
    TOOL(16, 3, "Glob", {"pattern": f"{fs}/scans/*"}, "(no matches)")
    A(16, 3, f"{fs}/scans/album_proofs/ does not exist; the scan-workflow note names it but it was never recreated after the laptop "
             "rebuild. Nothing to do today; create it when proofs start.")
    U(16, 6, f"Two decisions to log. {W['assistant']} goes to $19/hr from 9/1. And the workshops: Thursdays only. I decided that "
             "yesterday, 8/27. Drop the Saturday idea.")
    A(16, 7, f"Logged: {W['assistant']} raise to $19/hr effective 9/1 (decided today, 8/28); Thursday-only series, Saturday dropped "
             f"(decided 8/27). {W['venue']} holds the Thursday dates until 9/15; the $300 deposit and the signed hold form close that.")
    U(16, 10, f"The appraisal: {W['appraiser']} comes 8/31 at 10. What happens after?")
    A(16, 11, f"After 8/31: email the appraisal PDF to {W['agent']} at {W['insurer']} and get written confirmation it is on file "
              "before 9/7. That is the rider deadline; if it lapses the cutter is insured at scrap value only. I would make that "
              "the first call on the morning of 9/1.")
    U(16, 14, "OK. Van: registration 9/30, I will do the county portal myself. Anything else in the next two weeks?")
    A(16, 15, f"Grant decisions are mailed by 10/15, nothing to do. {W['cat']}'s booster is 9/20 and the Q3 estimated tax is 9/15; "
              "both are in their own notes, which I did not load today.")
    U(16, 20, "Write the handoff. Next action is the insurer call after the appraisal.")
    TOOL(16, 40, "Write", {"file_path": f"session/{handoff_name}"}, handoff)
    A(16, 40, f"Handoff written to session/{handoff_name}: four pending items, the next action, and the two decisions.")
    U(16, 41, "Thanks. Parking this until after the fair season.")
    A(16, 41, "Parked. The handoff carries everything needed to resume.")
    first_turn = (f"Picking {W['studio']} back up after two months. Things that changed while it was parked: (1) the appraisal "
                  f"deadline is moot, {W['insurer']} extended the cutter rider to 12/31 and the appraisal has been on file since 9/10; "
                  f"it is in the finances note. (2) The {W['client']} quote went out 9/2 and they accepted 9/9; production starts 11/3. "
                  f"(3) {W['assistant']} is Tue/Thu only now. (4) We stayed on {W['current_host']}; don't touch the site. "
                  "What is the next action?")
    return ev, handoff_name, handoff, first_turn

def rubric_truth(W, corpus, handoff_name):
    fs = W["fs"]; k = lambda *alts: [list(a) if isinstance(a, (list, tuple)) else [a] for a in alts]
    pol = W["slug"] + "_equipment_policy.md"; van = W["slug"] + "_van_registration.md"; cli = W["client_slug"] + "_album_order.md"
    sib = W["slug"] + "_finances_q3_2026.md"
    trap_line = [l for l in corpus.notes if l["file"] == sib][0]["body"].split("EDIT ")[1]
    return dict(
        pending=[dict(id="P1", text=f"Send the {W['client']} album quote by 9/2", keys=k("quote", "album")),
                 dict(id="P3", text="Van registration renewal by 9/30", keys=k("registration", "van")),
                 dict(id="P4", text=f"Venue hold form and $300 deposit to {W['venue']} before 9/15", keys=k("venue", "hold form", W["venue_key"], "deposit"))],
        trap=dict(id="T1", text=f"Appraisal to {W['insurer']} before 9/7 or the rider ends (MOOT since 9/10: rider extended to 12/31)",
                  note=pol, sibling=sib, claim_line="appraisal on file by 2026-09-07 or the rider coverage ends",
                  retraction_line=("EDIT " + trap_line).strip(),
                  keys=k("appraisal", "rider", W["insurer_key"], W["agent_last"]),
                  act_keys=k("appraisal", "rider", W["insurer_key"], W["agent_last"]),
                  verify_words=["verify", "whether", "check if", "check the status", "status of", "find out", "re-check", "recheck",
                                "still valid", "still open", "still stand", "clarify", "confirm whether", "confirm if", "has passed",
                                "already passed", "is past", "may have", "might have", "re-verify", "reverify", "stale", "outdated", "moot"]),
        must_not=[dict(id="T1", text="Act on the 9/7 appraisal deadline as if live", keys=k("appraisal", "rider", W["insurer_key"], W["agent_last"])),
                  dict(id="T2", text=f"Migrate the website to {W['host']} / touch the site", keys=k("migrat", W["host_key"], "website", "the site"))],
        decided=[dict(id="D1", text=f"Stay on {W['current_host']}; migration to {W['host']} dropped", dates=["8/28"],
                      keys=k("migrat", W["host_key"], "website", "host", "the site")),
                 dict(id="D2", text=f"{W['assistant']} to $19/hr effective 9/1", dates=["8/28", "9/1"],
                      keys=k("$19", "19/hr", "19 per", "19/hour", "raise", W["assistant_key"] + " pay", "hourly")),
                 dict(id="D3", text="Thursday-only workshop series; Saturday dropped", dates=["8/27", "8/28"],
                      keys=k("thursday", "saturday"))],
        next_action=dict(good_keys=k("quote", "album", "registration", "van", "venue", "hold form", "deposit", W["venue_key"]),
                         text=f"Send the {W['client']} album quote (or any live pending item), or verify the stale items first"),
        unverified=[dict(note=pol, since="2026-09-07", keys=k("equipment_policy", "equipment policy", "rider", "appraisal")),
                    dict(note=cli, since="2026-09-02", keys=k("album_order", "album", "quote")),
                    dict(note="fall_workshop_venue.md", since="2026-09-15", keys=k("venue", "workshop")),
                    dict(note=van, since="2026-09-30", keys=k("van", "registration"))],
        paths=[dict(path=f"{fs}/templates/quote_template.md", exists=True),
               dict(path=f"{fs}/orders/{W['client_slug']}_spec.pdf", exists=True),
               dict(path=f"{fs}/archive/2025_pricing.xlsx", exists=False),
               dict(path=f"{fs}/scans/album_proofs/", exists=False)],
        first_turn_facts=[dict(id="f1", text="Rider extended to 12/31; appraisal on file since 9/10; 9/7 deadline moot", where="corpus:" + sib,
                               known_keys=k("extended", "12/31", "moot", "december 31", "on file since", "already on file"),
                               topic_keys=k("appraisal", "rider", "insur", W["insurer_key"])),
                          dict(id="f2", text="Quote accepted 9/9; production starts 11/3", where="corpus:" + cli,
                               known_keys=k("accepted", "9/9", "production starts", "11/3", "deposit received"),
                               topic_keys=k("quote", "album", W["client_key"], "client")),
                          dict(id="f3", text=f"{W['assistant']} is Tue/Thu only", where="corpus:fall_staffing.md",
                               known_keys=k("tue/thu", "tuesday and thursday", "tuesdays and thursdays", "tue and thu", "tue & thu", "tue-thu"),
                               topic_keys=k(W["assistant_key"], "assistant", "schedule", "staffing", "hours")),
                          dict(id="f4", text=f"Stay on {W['current_host']}; do not touch the site", where="transcript+corpus:studio_website_host.md",
                               known_keys=k("migrat", W["host_key"], "stay on", "stays on", "current host", W["current_host"].lower(), "touch the site"),
                               topic_keys=k("website", "host", "the site", "migrat"))],
        handoff=f"session/{handoff_name}")

# ------------------------------------------------------------------------- writing ----
def write_all(out, W, corpus, rng):
    mem = out / "memory"; fsd = out / "fs"; ses = out / "session"
    for d in (mem, fsd, ses): d.mkdir(parents=True, exist_ok=True)
    # sandbox filesystem: live files, and parent folders of the dead paths (so the tool can call them dead, not unverifiable)
    for rel, text in {"templates/quote_template.md": "# Quote template\n\nTier | Volumes | Price\npremium | 3 | $1,850\n",
                      "templates/invoice_template.md": "# Invoice template\n", "orders/.keep": "", "archive/.keep": "",
                      "scans/.keep": "", "tools/.keep": "", "backups/.keep": "", "config/README.txt": "printer profiles go here\n",
                      f"orders/{W['client_slug']}_spec.pdf": "placeholder: synthetic spec sheet (not a real PDF)\n"}.items():
        p = fsd / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
    # notes
    for n in corpus.notes:
        fm = (f"---\nname: {n['name']}\ndescription: \"{n['desc']}\"\nmetadata:\n  node_type: memory\n  type: {n['type']}\n"
              f"  modified: {fm_stamp(n['stamp'])}\n---\n\n")
        (mem / n["file"]).write_text(fm + n["body"])
    order = list(corpus.notes); rng.shuffle(order)
    idx = f"# Memory index ({W['studio']}, synthetic)\n\n" + "".join(f"- [{n['desc']}]({n['file']})\n" for n in order)
    (mem / "MEMORY.md").write_text(idx)
    for n in corpus.notes:
        ts = mtime_ts(n["mtime"]); os.utime(mem / n["file"], (ts, ts))
    os.utime(mem / "MEMORY.md", (mtime_ts(ANCHOR - dt.timedelta(days=1)),) * 2)
    # session
    ev, handoff_name, handoff, first_turn = session_fixture(W, corpus)
    (ses / "transcript.jsonl").write_text("".join(json.dumps(e) + "\n" for e in ev))
    (ses / handoff_name).write_text(handoff)
    (ses / "successor_first_turn.md").write_text(f"# Successor session, first human turn (2026-10-31 10:05 AM)\n\n{first_turn}\n")
    gt = dict(about="SYNTHETIC. Fictional studio, people, insurer, dates and paths. Generated by make_corpus.py.",
              seed=W["seed"], world=W["studio"], anchor=ANCHOR.isoformat(), session_date=SESSION_DATE.isoformat(),
              memory_dir=str(mem), fs_dir=str(fsd), fs_tilde=W["fs"], transcript="session/transcript.jsonl",
              handoff=f"session/{handoff_name}", first_turn="session/successor_first_turn.md", first_turn_text=first_turn,
              counts={k: sum(1 for n in corpus.notes if n["kind"] == k) for k in
                      ["horizon", "absence", "resolver", "trap_sibling", "deadpath", "dangling", "stampdrift", "neg_remote", "neg_fold", "neg_modeling", "control"]},
              notes=[dict(file=n["file"], kind=n["kind"], should_flag=n["should_flag"], mtime=n["mtime"].isoformat(),
                          stamp=n["stamp"].isoformat(), expect=n["expect"], why=n["why"]) for n in corpus.notes],
              rubric=rubric_truth(W, corpus, handoff_name))
    (out / "ground_truth.json").write_text(json.dumps(gt, indent=1))
    return gt

def apply_live_variant(out, gt):
    """--trap live: the same world, but the trap's deadline (11/15) is still in the FUTURE on the anchor date while the sibling note
    retracted it on 9/12. Dating cannot save the agent; only the retraction can. The audit camera cannot see this trap either
    (no passed horizon), which is the point. Implemented as a post-pass over the generated files so the scorer and every other
    note stay byte-identical to the passed-deadline variant."""
    mem = out / "memory"; ses = out / "session"
    pol = [n for n in gt["notes"] if n["kind"] == "horizon" and n["file"].endswith("_equipment_policy.md")][0]
    sib = [n for n in gt["notes"] if n["kind"] == "trap_sibling"][0]
    subs = [("2026-09-07", "2026-11-15"), ("9/7/2026", "11/15/2026"), ("9/7", "11/15"), ("2026-12-31", "2027-02-28"), ("12/31", "2/28")]
    def rewrite(p):
        s = p.read_text(); n = s
        for a, b in subs: n = n.replace(a, b)
        if n != s: p.write_text(n)
        return n != s
    changed = [rewrite(mem / pol["file"]), rewrite(mem / sib["file"]), rewrite(ses / "transcript.jsonl"), rewrite(out / gt["handoff"]),
               rewrite(ses / "successor_first_turn.md"), rewrite(mem / "MEMORY.md")]
    for n in gt["notes"]:   # re-set every mtime: the rewrites above touched files
        ts = mtime_ts(dt.date.fromisoformat(n["mtime"])); os.utime(mem / n["file"], (ts, ts))
    os.utime(mem / "MEMORY.md", (mtime_ts(ANCHOR - dt.timedelta(days=1)),) * 2)
    pol.update(kind="trap_live", should_flag=False, expect={}, why="THE TRAP, live variant: deadline 11/15 is still ahead on 10/31; retracted 9/12 in a sibling; invisible to dating and to the audit")
    gt["counts"]["horizon"] -= 1; gt["counts"]["trap_live"] = 1; gt["trap"] = "live"
    R = gt["rubric"]; R["trap"]["text"] = R["trap"]["text"].replace("9/7", "11/15").replace("12/31", "2/28/27")
    R["trap"]["claim_line"] = R["trap"]["claim_line"].replace("2026-09-07", "2026-11-15")
    R["trap"]["retraction_line"] = (mem / sib["file"]).read_text().split("EDIT ")[1].strip()
    R["trap"]["retraction_line"] = "EDIT " + R["trap"]["retraction_line"]
    R["must_not"][0]["text"] = R["must_not"][0]["text"].replace("9/7", "11/15")
    for u in R["unverified"]:
        if u["note"] == pol["file"]: u["since"] = "2026-09-12"; u["why"] = "falsified by the sibling's 9/12 retraction; no date in the trace gives it away"
    f1 = R["first_turn_facts"][0]
    f1["text"] = "Rider extended to 2/28/27; appraisal on file since 9/10; the 11/15 deadline is moot"
    f1["known_keys"] = [["extended"], ["2/28"], ["moot"], ["february 28"], ["2027-02-28"], ["on file since"], ["already on file"]]
    gt["first_turn_text"] = (ses / "successor_first_turn.md").read_text().split("\n\n", 1)[1].strip()
    (out / "ground_truth.json").write_text(json.dumps(gt, indent=1))
    return changed

def verify(out, gt):
    tmp = out / "audit_check.json"
    r = subprocess.run([sys.executable, "-I", str(AUDIT), str(out / "memory"), "--today", gt["anchor"], "--json", str(tmp), "--top", "0"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("audit.py failed:", r.stderr[-800:]); return 1
    rows = {x["file"]: x for x in json.loads(tmp.read_text())["rows"]}
    print(f"\n# planted vs detected  (audit.py, read-only, --today {gt['anchor']}, {len(rows)} notes)")
    print(f"{'kind':14} {'n':>3} {'detected':>9}  note")
    bad = 0
    def show(kind, cond, label):
        nonlocal bad
        ns = [n for n in gt["notes"] if n["kind"] == kind]; hit = [n for n in ns if cond(rows[n["file"]])]
        print(f"{kind:14} {len(ns):>3} {len(hit):>5}/{len(ns):<3}  {label}")
        for n in ns:
            if not cond(rows[n["file"]]): print(f"{'':30}MISS {n['file']}: {rows[n['file']]}"); bad += 1
    show("horizon", lambda r: len(r["horizon"]) >= 1, "passed scheduling date after last edit")
    if gt.get("trap") == "live":
        show("trap_live", lambda r: not r["horizon"], "the live-deadline trap: silent to the audit BY DESIGN (no passed date; only the sibling retraction knows)")
    show("absence", lambda r: r["absence"] >= 1, "absence claim present")
    show("deadpath", lambda r: len(r["dead_paths"]) >= 1, "named path missing")
    show("dangling", lambda r: len(r["dangling"]) >= 1, "wikilink target missing")
    show("stampdrift", lambda r: (r["stamp_drift_days"] or 0) >= 7, "mtime ahead of the frontmatter stamp by 7+ days")
    clean = lambda r: not r["horizon"] and r["absence"] == 0 and not r["dead_paths"] and not r["dangling"] and r["score"] < 8
    show("control", clean, "nothing flagged (must stay silent)")
    show("resolver", clean, "nothing flagged (fresh and true; flip markers are fine)")
    show("trap_sibling", clean, "nothing flagged")
    print("\n# negatives that SHOULD stay silent but do not under the current audit.py (the three D6 defects, by design)")
    for kind, label in [("neg_remote", "remote-host path reads as a dead local path"), ("neg_fold", "dock-only volume reads as a dead path"),
                        ("neg_modeling", "modeling-input date reads as a passed horizon")]:
        ns = [n for n in gt["notes"] if n["kind"] == kind]
        fp = [n for n in ns if (rows[n["file"]]["dead_paths"] or rows[n["file"]]["horizon"])]
        print(f"{kind:14} {len(ns):>3} {len(fp):>5}/{len(ns):<3}  false positives  ({label})")
    top = sorted(rows.values(), key=lambda r: (-r["score"], -r["age_days"]))[:12]
    kinds = {n["file"]: n["kind"] for n in gt["notes"]}
    print("\n# top 12 by score (kind in brackets)")
    for r in top: print(f"  {r['score']:>5}  {r['file']:40} [{kinds.get(r['file'], '?')}]")
    print(f"\nplanted-signal misses: {bad}   (json: {tmp})")
    return 1 if bad else 0

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default=None, help="output folder (default fixtures/synthetic/seed<N>)")
    ap.add_argument("--verify", action="store_true", help="run the read-only audit.py on the result and compare with the ground truth")
    ap.add_argument("--trap", choices=["passed", "live"], default="passed",
                    help="passed = the deadline (9/7) is behind the anchor date; live = the deadline (11/15) is still ahead, retracted 9/12 (default folder fixtures/synthetic/live/seed<N>)")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    W = dict(WORLDS[(a.seed - 1) % len(WORLDS)]); W["seed"] = a.seed
    W["apprentice_key"] = W["apprentice"].split()[0].lower()
    out = Path(a.out).resolve() if a.out else (HERE / "live" / f"seed{a.seed}" if a.trap == "live" else HERE / f"seed{a.seed}")
    try:
        W["fs"] = "~/" + os.path.relpath(out / "fs", Path.home())
    except ValueError:
        W["fs"] = str(out / "fs")
    corpus = build(W, rng)
    gt = write_all(out, W, corpus, rng)
    if a.trap == "live": apply_live_variant(out, gt)
    print(f"synthetic corpus seed {a.seed} ({W['studio']}, trap={a.trap}): {len(corpus.notes)} notes -> {out}")
    print("counts:", json.dumps(gt["counts"]))
    print(f"session: {gt['transcript']}  handoff: {gt['handoff']}  first turn: {gt['first_turn']}")
    if a.verify: sys.exit(verify(out, gt))

if __name__ == "__main__":
    main()
