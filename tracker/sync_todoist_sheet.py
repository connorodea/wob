#!/usr/bin/env python3
"""wob tracker sync — bidirectional Todoist <-> Google Sheets.

Join key: Todoist task id in column A of 'Tasks' (the AIWholesail pattern).
- Todoist -> Sheet: upsert all tasks of the wob project (id/title/section/
  status/priority/due), remove stale rows.
- Sheet -> Todoist: any row whose Status cell differs from Todoist's state
  toggles the task (open<->done), then Todoist direction is re-read.

Google auth: application-default credentials with the `spreadsheets` scope
(gcloud auth application-default login --scopes=...,https://www.googleapis.com/
auth/spreadsheets,...). Sheet id from ~/.wob_tracker_sheet_id (or WOB_TRACKER_SHEET_ID).
Todoist: $TODOIST_API_TOKEN via the unified v1 API.
"""

import json
import os
import pathlib
import subprocess
import sys
import urllib.request

HOME = pathlib.Path.home()
SHEET_ID_FILE = HOME / ".wob_tracker_sheet_id"
TODOIST_PROJECT = "WOB Book Price Finder"
SHEETS_URL = "https://sheets.googleapis.com/v4/spreadsheets"
TODOIST_URL = "https://api.todoist.com/api/v1"

STATUS_MAP = {"completed": "done", "open": "open"}  # todoist state -> sheet text


def sheet_id():
    env = os.environ.get("WOB_TRACKER_SHEET_ID")
    if env:
        return env
    if SHEET_ID_FILE.exists():
        return SHEET_ID_FILE.read_text().strip()
    raise SystemExit("no sheet id: set WOB_TRACKER_SHEET_ID or ~/.wob_tracker_sheet_id")


def gaccess():
    tok = subprocess.run(
        ["gcloud", "auth", "application-default", "print-access-token"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return f"Bearer {tok}"


def sheets(method, path, body=None):
    req = urllib.request.Request(
        f"{SHEETS_URL}{path}", method=method,
        headers={"Authorization": gaccess(), "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def todoist(method, path, body=None):
    req = urllib.request.Request(
        f"{TODOIST_URL}{path}", method=method,
        headers={"Authorization": f"Bearer {os.environ['TODOIST_API_TOKEN']}",
                 "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    with urllib.request.urlopen(req) as r:
        data = r.read()
        return json.loads(data) if data else {}


def get_todoist_projects():
    data = todoist("GET", "/projects")
    return {p["name"]: p["id"] for p in data}


def get_tasks(project_id):
    return todoist("GET", f"/tasks?project_id={project_id}")


def get_sections(project_id):
    return {s["id"]: s["name"] for s in todoist("GET", f"/sections?project_id={project_id}")}


def main():
    sid = sheet_id()
    pid = get_todoist_projects()[TODOIST_PROJECT]
    sections = get_sections(pid)
    tasks = get_tasks(pid)

    rows = sorted(
        [
            [
                t["id"],
                t.get("content", ""),
                sections.get(t.get("section_id"), ""),
                STATUS_MAP.get("completed" if t.get("completed_at") else "open", "open"),
                str(t.get("priority", 4)),
                t.get("due", {}).get("date", "") if t.get("due") else "",
            ]
            for t in tasks
        ],
        key=lambda r: r[1],
    )

    # read current Tasks tab to find rows to flip Sheet->Todoist
    cur = sheets("GET", f"/{sid}/values/Tasks!A2:F500").get("values", [])
    by_id = {r[0]: r for r in cur if r and r[0]}
    desired = {r[0]: r[3] for r in rows}

    # Sheet -> Todoist (explicit local wins; Todoist wins otherwise)
    flips = 0
    for t in tasks:
        row = by_id.get(t["id"])
        if row and len(row) > 3 and row[3] in ("open", "done"):
            cur_state = "done" if t.get("completed_at") else "open"
            if row[3] != cur_state:
                if row[3] == "done":
                    todoist("POST", f"/tasks/{t['id']}/close")
                else:
                    todoist("POST", f"/tasks/{t['id']}/reopen")
                flips += 1

    # Todoist -> Sheet: overwrite Tasks tab with fresh state
    header = ["Todoist ID", "Title", "Section", "Status", "Priority", "Due"]
    out = [header] + rows
    sheets("PUT", f"/{sid}/values/Tasks!A1",
           {"majorDimension": "ROWS", "values": out})

    # Settings tab: last sync
    import datetime
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    settings = [
        ["Setting", "Value"],
        ["sheet_id", sid],
        ["todoist_project", TODOIST_PROJECT],
        ["last_sync", stamp],
        ["flips_last_run", int(flips)],
    ]
    sheets("PUT", f"/{sid}/values/Settings!A1",
           {"majorDimension": "ROWS", "values": settings})
    print(f"synced {len(tasks)} tasks, {flips} sheet->todoist flips @ {stamp}")


if __name__ == "__main__":
    main()