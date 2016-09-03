from __future__ import print_function
import httplib2
import os

import csv

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

from datetime import datetime
from dateutil import tz

import todoist

class todoistgcalsync:
	
	todoist_api = None
	todoist_api_token = None
	todoist_sync_data = []
	
	#http = None
	credentials = None
	gcal_service = None
	target_calendar_id = None
	target_calendar_summary = None
	
	fieldnames = []
	watch_data = []
	
	timezone_str = None
	timezone = None
	
	data_file = None
	
	def __init__(self,
				 todoist_api_token,
				 target_calendar_summary = 'Todoist',
				 target_calendar_id_file = 'gcalid.txt',
				 data_file = 'data.csv',
				 fieldnames = ['TodoID', 'EventID', 'summary', 'datetime']):
		
		self.todoist_api_token = todoist_api_token
		self.target_calendar_summary = target_calendar_summary
		self.target_calendar_id_file = target_calendar_id_file
		self.data_file = data_file
		self.fieldnames = fieldnames
		
		# Initialize Todoist API
		self.initialize_todoist_api()
		
		# Initialize Google Calendar Service
		
		self.initialize_gcal_service()
		
		# Get Google Calendar target
		self.calendar_target_id = self.get_target_calendar_id()
	
	def initialize_todoist_api(self):
		self.todoist_api = todoist.TodoistAPI(self.todoist_api_token)
		
		# Initialize timezone from Todoist
		self.timezone_str = self.todoist_api.state['user']['tz_info']['timezone']
		self.timezone = tz.gettz(self.timezone_str)
		
	def initialize_gcal_service(self):
		self.credentials = self.get_credentials()
		http = self.credentials.authorize(httplib2.Http())
		self.gcal_service = discovery.build('calendar', 'v3', http=http)
	
	def get_credentials(self):
		"""Gets valid user credentials from storage.

		If nothing has been stored, or if the stored credentials are invalid,
		the OAuth2 flow is completed to obtain the new credentials.

		Returns:
			Credentials, the obtained credential.
		"""
		home_dir = os.path.expanduser('~')
		credential_dir = os.path.join(home_dir, '.credentials')
		if not os.path.exists(credential_dir):
			os.makedirs(credential_dir)
		credential_path = os.path.join(credential_dir,
									   'calendar-python-quickstart.json')

		store = oauth2client.file.Storage(credential_path)
		credentials = store.get()
		if not credentials or credentials.invalid:
			flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
			flow.user_agent = APPLICATION_NAME
			if flags:
				credentials = tools.run_flow(flow, store, flags)
			else: # Needed only for compatibility with Python 2.6
				credentials = tools.run(flow, store)
			print('Storing credentials to ' + credential_path)
		return credentials
	
	def get_target_calendar_id(self):
		# Search for file with id
		if os.path.exists(self.target_calendar_id_file):
			with open(self.target_calendar_id_file) as idfile:
				return idfile.read()
		
		# No file, find calendar id
		page_token = None
		while True:
			# Search through calendar list
			calendar_list = self.gcal_service.calendarList().list(pageToken=page_token).execute()
			for entry in calendar_list['items']:
				if entry['summary'] == self.target_calendar_summary:
					# Entry found, make id file and return
					with open(self.target_calendar_id_file, 'w') as idfile:
						idfile.write(entry['id'])
					return entry['id']
			page_token = calendar_list.get('nextPageToken')
			if not page_token:
				break
		
		# No calendar, create a new one and make id file
		calendar = {
			'summary': self.target_calendar_summary,
			'timeZone': self.timezone_str
		}
		new_calendar = self.gcal_service.calendars().insert(body=calendar).execute()
		with open(self.target_calendar_id_file, 'w') as idfile:
			idfile.write(new_calendar['id'])
						
		return new_calendar['id']
	
	def load_data(self):
		if os.path.exists(self.data_file):
			with open(self.data_file) as csvfile:
				reader = csv.DictReader(csvfile, self.fieldnames)
				self.watch_data.extend(reader)
			
		
	def write_data(self):
		with open(self.data_file, 'w') as csvfile:
			writer = csv.DictWriter(csvfile, self.fieldnames)
			for row in self.watch_data:
				writer.writerow(row)
			
	def parse_todoist_date(self, date_str):
		return datetime.strptime(date_str, '%a %d %b %Y %H:%M:%S +0000')
	
	def parse_google_datetime(self, date_str):
		return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S+0000')
	
	def parse_google_date(self, date_str):
		return datetime.strptime(date_str, '%Y-%m-%d')
		
	def format_google_datetime(self, date_object):
		return datetime.strftime(date_object, '%Y-%m-%dT%H:%M:%S+0000')
		#return date_object.isoformat('T')
		
	def format_google_date(self, date_object):
		return datetime.strftime(date_object, '%Y-%m-%d')
	
	def lookup_row(self, **kw):
		for row in self.watch_data:
			for k,v in kw.iteritems():
				if row[k] != str(v): break
			else:
				return row
		return None
	
	def force_todoist_sync_data(self):
		### Update Google calendar to reflect Todoist sync data indiscriminately 
		
		for item in self.todoist_sync_data['items']:
			
			row = None
			new_event = None
			summary = None
			date_object = None
			
			# Find data entry (if it exists)
			row = self.lookup_row(TodoID=item['id'])
			
			# Data entry exists ==> update existing event
			if row:
				
				# Only update
				if item['due_date_utc']:
				
					# Check for changes in summary
					if row['summary'] <> item['content']:
						summary = item['content']
					
					# Check for changes in date
					todoist_date_object = self.parse_todoist_date(item['due_date_utc'])
					if self.parse_google_datetime(row['datetime']) <> todoist_date_object:
						date_object = todoist_date_object
					
					# Run only if there is a change
					if summary or date_object:
						if item['all_day']:
							self.update_all_day_event(row, summary, date_object)
						else:
							self.update_event(row, summary, date_object)
				
				# Date removed ==> delete
				else:
					# Delete event
						self.gcal_service.events().delete(calendarId=self.calendar_target_id, eventId=row['EventID']).execute()
					# Delete data entry
						self.watch_data.remove(row)
					
			# Data entry does not exist ==> create new (if it has a date)
			elif item['due_date_utc']:
				
				if item['all_day']:
					self.new_all_day_event(item)
				else:
					self.new_event(item)

	def new_event(self, item):
		# Parse Todoist date string
		date_object = self.parse_todoist_date(item['due_date_utc'])
		
		# Tell datetime object it's in UTC (otherwise it's 'naive')
		#date_object = date_object.replace(tzinfo=tz.gettz('UTC'))
		
		# Convert datetime object to timezone
		#date_object = date_object.astimezone(tz.gettz(self.timezone_str))
		
		# Format datetime object as Google date string
		google_date_str = self.format_google_datetime(date_object)
		
		event_body = {
			'summary': item['content'],
			'start': {
				'dateTime': google_date_str,
				'timeZone': self.timezone_str
			},
			'end': {
				'dateTime': google_date_str,
				'timeZone': self.timezone_str
			}
		}
		
		# Publish event to calendar
		event = self.gcal_service.events().insert(calendarId=self.calendar_target_id, body=event_body).execute()
		
		# Create data entry
		entry = {
			'TodoID': item['id'],
			'EventID': event['id'],
			'summary': item['content'],
			'datetime': self.format_google_datetime(date_object)
		}
		
		self.watch_data.append(entry)
		
		# Return event to extract info
		return event
	
	def new_all_day_event(self, item):	
		# Parse Todoist date string
		date_object = self.parse_todoist_date(item['due_date_utc'])
		
		# TODO: Figure out why this works in order to simplify (cp. new_event definition)
		date_object = date_object.replace(tzinfo=self.timezone)
		date_object = date_object.astimezone(tz.gettz('UTC'))
		
		#Format for Google Calendar
		google_date_str = self.format_google_date(date_object)
		
		event_body = {
			'summary': item['content'],
			'start': {
				'date': google_date_str,
				'timeZone': self.timezone_str
			},
			'end': {
				'date': google_date_str,
				'timeZone': self.timezone_str
			}
		}
		
		# Publish event to calendar
		event = self.gcal_service.events().insert(calendarId=self.calendar_target_id, body=event_body).execute()
		
		# Create data entry
		entry = {
			'TodoID': item['id'],
			'EventID': event['id'],
			'summary': item['content'],
			'datetime': self.format_google_datetime(date_object)
		}
		
		self.watch_data.append(entry)
		
		# Return event to extract info
		return event
	
	def update_event(self, row, summary = None, date_object = None):
		# Get event
		event = self.gcal_service.events().get(calendarId=self.calendar_target_id, eventId=row['EventID']).execute()
		
		# Prepare new data entry
		new_row = row
		
		if date_object:
			# TODO: Figure out why this works in order to simplify (cp. new_event definition)
			#date_object = date_object.replace(tzinfo=self.timezone)
			#date_object = date_object.astimezone(tz.gettz('UTC'))
		
			#Format for Google Calendar
			google_date_str = self.format_google_datetime(date_object)
		
			# Update event
			event['start'] = {
				'dateTime': google_date_str,
				'timeZone': self.timezone_str
			}
			event['end'] = {
				'dateTime': google_date_str,
				'timeZone': self.timezone_str
			}
			
			# Update data entry
			new_row['datetime'] = self.format_google_datetime(date_object)
		
		if summary:
			# Update event
			event['summary'] = summary
			
			# Update data entry
			new_row['summary'] = summary
		
		# Publish event changes
		event = self.gcal_service.events().update(calendarId=self.calendar_target_id, eventId=row['EventID'], body=event).execute()
		
		# Replace data entry
		self.watch_data.remove(row)
		self.watch_data.append(new_row)
		
		return event
	
	def update_all_day_event(self, row, summary = None, date_object = None):
		# Get event
		event = self.gcal_service.events().get(calendarId=self.calendar_target_id, eventId=row['EventID']).execute()
		
		# Prepare new data entry
		new_row = row
		
		if date_object:
			# TODO: Figure out why this works in order to simplify (cp. new_event definition)
			date_object = date_object.replace(tzinfo=self.timezone)
			date_object = date_object.astimezone(tz.gettz('UTC'))
		
			#Format for Google Calendar
			google_date_str = self.format_google_date(date_object)
		
			# Update event
			event['start'] = {
				'date': google_date_str,
				'timeZone': self.timezone_str
			}
			event['end'] = {
				'date': google_date_str,
				'timeZone': self.timezone_str
			}
			
			# Update data entry
			new_row['datetime'] = self.format_google_datetime(date_object)
		
		if summary:
			# Update event
			event['summary'] = summary
			
			# Update data entry
			new_row['summary'] = summary
		
		# Publish event changes
		event = self.gcal_service.events().update(calendarId=self.calendar_target_id, eventId=row['EventID'], body=event).execute()
		
		# Replace data entry
		self.watch_data.remove(row)
		self.watch_data.append(new_row)
		
		return event
	
	def initialize_data(self):
		# First-time data initialization:

		for item in self.todoist_api.state['items']:
			if item['due_date_utc']:
				
				event = None
				date_object = self.parse_todoist_date(item['due_date_utc'])
				
				if item['all_day']:
					event = self.new_all_day_event(item)
				else:
					event = self.new_event(item)
				
				entry = {
					'TodoID': item['id'],
					'EventID': event['id'],
					'summary': item['content'],
					'datetime': self.format_google_datetime(date_object)
				}
				
				self.watch_data.append(entry)