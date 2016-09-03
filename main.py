
import os

from todoistgcalsync import todoistgcalsync
	
def main():
	
	token = None
	
	with open('token.txt') as token_file:
		token = token_file.read()
	
	syncservice = todoistgcalsync(token)
	
	if not os.path.isfile(syncservice.data_file):
		syncservice.initialize_data()
	else:
		syncservice.load_data()
		syncservice.todoist_sync_data = syncservice.todoist_api.sync()
		syncservice.force_todoist_sync_data()
		
	syncservice.write_data()
			
main()