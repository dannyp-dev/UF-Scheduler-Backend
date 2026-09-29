# UF Scheduler Backend

This is a fork of [andychen482/UF-Scheduler-Backend](https://github.com/andychen482/UF-Scheduler-Backend). It serves course search and prerequisite graphs for the UF Scheduler frontend.

## Current data limitation

As checked on September 29, 2026, the public ONE.UF Schedule of Courses endpoint returns `meetTimes: []` and `openSeats: null` for in-person sections. The old scraper kept saving those incomplete results. A timetable cannot reliably detect overlapping classes without section meeting times. This repository does not contain a workaround for UF login and does not require students to share credentials or session cookies.

To restore timetable generation, obtain a current section schedule export that UF permits this project to use. The export must match the ONE.UF course JSON format and include `sections[].meetTimes[]` with `meetDays`, `meetTimeBegin`, and `meetTimeEnd`. A list of course objects or a list of ONE.UF response pages (each containing `COURSES`) is accepted. Remove any student-specific data before sharing an export.

Import it with:

```bash
python pythonScripts/import_schedule.py /path/to/authorized-export.json 26 fall
```

The importer normalizes times to 24-hour format and writes `courses/UF_Imported_26_fall_final.json`. By default, it refuses an empty export or one with missing times for any in-person section, and it does not replace existing course data on failure. If UF has genuine to-be-announced sections, review them before lowering the threshold with `--minimum-coverage`. Keep the export for each term current as UF changes sections.

The old scheduled GitHub Actions scraper has been removed because the public feed no longer supplies enough data for schedule generation. Add an authorized, maintainable data source before scheduling imports again.

## Running locally

Install `requirements.txt`, then run `python server.py` from the repository root. `GET /api/terms` lists the terms loaded at startup and the number of sections with meeting times. `POST /api/get_courses` accepts `searchTerm`, `year`, `term`, `itemsPerPage`, and `startFrom`. The prerequisite graph endpoint remains `POST /generate_a_list`.

Run the import checks with:

```bash
python -m unittest discover -s tests
```
