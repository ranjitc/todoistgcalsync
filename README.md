# todoistgcalsync
A utility to sync Todoist events to Google Calendar written in Python

## Why
This utility was born out of the rage and mourning of the death of Sunrise Calendar. Moving events around in the calendar was the #1 reason why I used it. Apparently the Premium features don't include this kind of bi-directional support.

## Design goals
- Facilitate bi-directional sync between Todoist tasks and a dedicated Todoist calendar:
    - Due date changes
    - Summary/content changes
    - Preserve custom task lengths
    - Premium related data changes?
- Set up as a daemon to run on a home server to continuously update.

## How it currently works
- There is a 'todoistgcalsync' object that houses everything. It's still very rough.
- Right now it only updates the calendar from Todoist data updates (not the other way). But, this is a step up from the .ics functionality for Premium users (which I'm not) because of its API interaction with a user's calendar.
- Relies on setting up your own API configuration with Google. It finds (or makes) a calendar named by default 'Todoist', and keeps the id in a text file.
- Requires knowing your Todoist API token
- Stores a list of known task/events in a csv file (this is probably not very efficient)

## About me
I'm a CS student, but I haven't worked with Python for a long time, so some things are a bit awkward right now.
