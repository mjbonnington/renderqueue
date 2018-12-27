#!/usr/bin/python

# database.py
#
# Mike Bonnington <mjbonnington@gmail.com>
# (c) 2016-2018
#
# Interface for the Render Queue database.


import glob
import json
import os
import uuid

# Import custom modules
import oswrapper
import sequence
# import ui_template as UI


# class RenderJob(UI.SettingsData):
# 	""" Class to hold an render job.
# 	"""


# class RenderTask(UI.SettingsData):
# 	""" Class to hold an individual task.
# 	"""


class RenderQueue():
	""" Class to manage the render queue database.
	"""
	def __init__(self, location=None):
		self.db_root = location
		self.db_jobs = os.path.join(location, 'jobs')
		self.db_tasks = os.path.join(location, 'tasks')
		self.db_queued = os.path.join(location, 'tasks', 'queued')
		self.db_completed = os.path.join(location, 'tasks', 'completed')
		self.db_failed = os.path.join(location, 'tasks', 'failed')
		self.db_workers = os.path.join(location, 'workers')
		print("Connecting to render queue database at: " + location)
		# Create folder structure (could be more dynamic)
		oswrapper.createDir(self.db_jobs)
		oswrapper.createDir(self.db_tasks)
		oswrapper.createDir(self.db_queued)
		oswrapper.createDir(self.db_completed)
		oswrapper.createDir(self.db_failed)
		oswrapper.createDir(self.db_workers)


	def newJob(self, **kwargs):
		""" Create a new render job and associated tasks.
			Generates a JSON file with the job UUID to hold data for the
			render job. Also generates a JSON file for each task. These are
			placed in the 'queued' subfolder ready to be picked up by workers.
		"""
		jobID = uuid.uuid4().hex  # generate UUID
		kwargs['jobID'] = jobID

		# Write job data file
		datafile = os.path.join(self.db_jobs, '%s.json' %jobID)
		with open(datafile, 'w') as f:
			json.dump(kwargs, f, indent=4)

		# Write tasks and place in queue
		tasks = kwargs['tasks']
		for i in range(len(kwargs['tasks'])):
			taskdata = {}
			taskdata['jobID'] = jobID
			taskdata['taskNo'] = i
			taskdata['frames'] = tasks[i]
			# taskdata['command'] = kwargs['command']
			# taskdata['flags'] = kwargs['flags']

			datafile = os.path.join(self.db_queued, 
				'%s_%s.json' %(jobID, str(i).zfill(4)))
			with open(datafile, 'w') as f:
				json.dump(taskdata, f, indent=4)


	def deleteJob(self, jobID):
		""" Delete a render job and associated tasks.
			Searches for all JSON files with job UUID under the queue folder
			structure and deletes them. Also kills processes for tasks that
			are rendering.
		"""
		datafile = os.path.join(self.db_jobs, '%s.json' %jobID)
		oswrapper.recurseRemove(datafile)

		path = '%s/*/*/%s_*.json' %(self.db_root, jobID)
		for filename in glob.glob(path):
			if 'workers' in filename:
				print("Task %s currently rendering." %filename)
			oswrapper.recurseRemove(filename)
		return True


	def archiveJob(self, jobID):
		""" Archive a render job and associated tasks.
			Moves all files associated with a particular job UUID into a
			special archive folder.
		"""
		pass


	def requeueJob(self, jobID):
		""" Requeue a render job and associated tasks.
		"""
		#statuses = ['queued', 'working', 'completed', 'failed']
		path = '%s/*/*/%s_*.json' %(self.db_root, jobID)
		for filename in glob.glob(path):
			if 'queued' not in filename:
				oswrapper.move(filename, self.db_queued)


	def getJobs(self):
		""" Read jobs.
		"""
		jobs = []
		path = '%s/jobs/*.json' %self.db_root
		for filename in glob.glob(path):
			with open(filename, 'r') as f:
				jobs.append(json.load(f))
		return jobs


	def getTasks(self, jobID):
		""" Read tasks for a specified job.
		"""
		tasks = []
		#statuses = ['queued', 'working', 'completed', 'failed']
		path = '%s/*/*/%s_*.json' %(self.db_root, jobID)
		for filename in glob.glob(path):
			if 'workers' in filename:
				status = 'Working'
			elif 'queued' in filename:
				status = 'Queued'
			elif 'completed' in filename:
				status = 'Done'
			elif 'failed' in filename:
				status = 'Failed'
			else:
				status = 'Unknown'
			with open(filename, 'r') as f:
				taskdata = json.load(f)
				taskdata['status'] = status
				tasks.append(taskdata)
		return tasks


	def getQueuedTasks(self, jobID):
		""" Return all queued tasks for a specified job.
		"""
		tasks = []
		path = '%s/%s_*.json' %(self.db_queued, jobID)
		for filename in glob.glob(path):
			with open(filename, 'r') as f:
				taskdata = json.load(f)
				tasks.append(taskdata)
		return tasks


	# def getJob(self, jobID):
	# 	""" Read job.
	# 	"""
	# 	datafile = 'queue/jobs/%s.json' %jobID
	# 	with open(datafile) as f:
	# 		data = json.load(f)
	# 	return data


	def getPriority(self, jobID):
		""" Get the priority of a render job.
		"""
		filename = os.path.join(self.db_jobs, '%s.json' %jobID)
		with open(filename, 'r') as f:
			job = (json.load(f))
		return job['priority']


	def setPriority(self, jobID, priority):
		""" Set the priority of a render job.
		"""
		filename = os.path.join(self.db_jobs, '%s.json' %jobID)
		with open(filename, 'r') as f:
			job = (json.load(f))
		if 0 <= priority <= 100:
			# Only write file if priority has changed
			if job['priority'] != priority:
				job['priority'] = priority
				with open(filename, 'w') as f:
					json.dump(job, f, indent=4)
		# elif priority == 0:
		# 	job['priorityold'] = job['priority']
		# 	job['priority'] = priority


	def dequeueJob(self):
		""" Find a job with the highest priority that isn't paused or
			completed, and return the first queued task.
		"""
		# Get jobs and sort by priority
		jobs = self.getJobs()
		from operator import itemgetter
		for job in sorted(jobs, key=itemgetter('priority'), reverse=True):
			print("[Priority %d] Job ID %s: %s" %(job['priority'], job['jobID'], job['jobName']))

			# Get queued tasks, sort by ID, return first result
			tasks = self.getQueuedTasks(job['jobID'])
			if tasks:
				return sorted(tasks, key=itemgetter('taskNo'))[0]

		# for priority in range(100, 0, -1):  # Iterate over range starting at 100 and ending at 1 (zero is omitted)

		# 	elements = self.root.findall("./job/[priority='%s']" %priority) # get all <job> elements with the highest priority
		# 	if elements is not None:
		# 		for element in elements:
		# 			#print "[Priority %d] Job ID %s: %s (%s)" %(priority, element.get('id'), element.find('name').text, element.find('status').text),
		# 			if element.find('status').text != "Done":
		# 				if element.find("task/[status='Queued']") is not None: # does this job have any queued tasks?
		# 					#print "This will do, let's render it!"
		# 					return element
		# 			#print "Not yet, keep searching..."

		return None


	# def dequeueTask(self, jobID, hostID):
	# 	""" Dequeue the next queued task belonging to the specified job, mark
	# 		it as 'Working' (in-progress), and return the task ID and the
	# 		frame range.
	# 	"""
	# 	return False, False
	# 	# self.loadXML(quiet=True) # reload XML data
	# 	# element = self.root.find("./job[@id='%s']/task/[status='Queued']" %jobID) # get the first <task> element with 'Queued' status
	# 	# #element = self.root.find("./job[@id='%s']/task" %jobID) # get the first <task> element
	# 	# if element is not None:
	# 	# 	#if element.find('status').text is not "Done":
	# 	# 	element.find('status').text = "Working"
	# 	# 	element.find('worker').text = str(hostID)
	# 	# 	self.saveXML()
	# 	# 	return element.get('id'), element.find('frames').text

	# 	# else:
	# 	# 	return False, False


	def dequeueTask(self, jobID, taskID, workerID):
		"""
		"""
		filename = os.path.join(self.db_queued, '%s_%s.json' %(jobID, str(taskID).zfill(4)))
		dst = os.path.join(self.db_workers, workerID)

		oswrapper.move(filename, dst)


	def updateTaskStatus(self, jobID, taskID, progress):
		""" Update task progress.
		"""
		pass
		# self.loadXML(quiet=True) # reload XML data
		# element = self.root.find("./job[@id='%s']/task[@id='%s']" %(jobID, taskID)) # get the <task> element
		# if element is not None:
		# 	if "Working" in element.find('status').text: # only update progress for in-progress tasks
		# 		element.find('status').text = "[%d%%] Working" %progress
		# 		self.saveXML()


	def completeTask(self, jobID, taskID, worker=None, taskTime=0):
		""" Mark the specified task as 'Done'.
		"""
		path = '%s/*/*/%s_%s.json' %(self.db_root, jobID, str(taskID).zfill(4))
		for filename in glob.glob(path):
			if 'completed' not in filename:
				oswrapper.move(filename, self.db_completed)

		# self.loadXML(quiet=True) # reload XML data
		# element = self.root.find("./job[@id='%s']/task[@id='%s']" %(jobID, taskID)) # get the <task> element
		# if element is not None:
		# 	if element.find('status').text == "Done": # do nothing if status is 'Done'
		# 		return
		# 	# elif element.find('status').text == "Working": # do nothing if status is 'Working'
		# 	# 	return
		# 	else:
		# 		element.find('status').text = "Done"
		# 		element.find('worker').text = str(worker)
		# 		element.find('totalTime').text = str(taskTime)
		# 		self.saveXML()


	def failTask(self, jobID, taskID, worker=None, taskTime=0):
		""" Mark the specified task as 'Failed'.
		"""
		path = '%s/*/*/%s_%s.json' %(self.db_root, jobID, str(taskID).zfill(4))
		for filename in glob.glob(path):
			if 'failed' not in filename:
				oswrapper.move(filename, self.db_failed)

		# self.loadXML(quiet=True) # reload XML data
		# element = self.root.find("./job[@id='%s']/task[@id='%s']" %(jobID, taskID)) # get the <task> element
		# if element is not None:
		# 	if element.find('status').text == "Failed": # do nothing if status is 'Failed'
		# 		return
		# 	# elif element.find('status').text == "Working": # do nothing if status is 'Working'
		# 	# 	return
		# 	else:
		# 		element.find('status').text = "Failed"
		# 		element.find('worker').text = str(worker)
		# 		element.find('totalTime').text = str(taskTime)
		# 		self.saveXML()


	def requeueTask(self, jobID, taskID):
		""" Requeue the specified task, mark it as 'Queued'.
		"""
		path = '%s/*/*/%s_%s.json' %(self.db_root, jobID, str(taskID).zfill(4))
		for filename in glob.glob(path):
			if 'queued' not in filename:
				oswrapper.move(filename, self.db_queued)

		# self.loadXML(quiet=True) # reload XML data
		# element = self.root.find("./job[@id='%s']/task[@id='%s']" %(jobID, taskID)) # get the <task> element
		# if element.find('status').text == "Queued": # do nothing if status is 'Queued'
		# 	return
		# # elif element.find('status').text == "Working": # do nothing if status is 'Working'
		# # 	return
		# else:
		# 	element.find('status').text = "Queued"
		# 	element.find('totalTime').text = ""
		# 	element.find('worker').text = ""
		# 	self.saveXML()


	def combineTasks(self, jobID, taskIDs):
		""" Combine the specified tasks.
		"""
		print(jobID, taskIDs)
		if len(taskIDs) < 2:
			print("Error: Need at least two tasks to combine.")
			return None

		tasks_to_delete = []
		frames = []
		for taskID in taskIDs:
			filename = os.path.join(self.db_queued, 
				'%s_%s.json' %(jobID, str(taskID).zfill(4)))
			with open(filename, 'r') as f:
				taskdata = json.load(f)
			frames += sequence.numList(taskdata['frames'])
			if taskID == taskIDs[0]:  # Use data from first task in list
				newtaskdata = taskdata
			else:
				tasks_to_delete.append(filename)  # Mark other tasks for deletion

		# Sanity check on new frame range
		try:
			start, end = sequence.numRange(frames).split("-")
			start = int(start)
			end = int(end)
			assert start<end, "Error: Start frame must be smaller than end frame."
			newframerange = "%s-%s" %(start, end)
			print("New frame range: " + newframerange)
		except:
			print("Error: Cannot combine tasks - combined frame range must be contiguous.")
			return None

		# Delete redundant tasks
		for filename in tasks_to_delete:
			oswrapper.recurseRemove(filename)

		# Write new task
		newtaskdata['frames'] = newframerange
		datafile = os.path.join(self.db_queued, 
			'%s_%s.json' %(jobID, str(taskIDs[0]).zfill(4)))
		with open(datafile, 'w') as f:
			json.dump(newtaskdata, f, indent=4)

		return taskIDs[0]


	def newWorker(self, **kwargs):
		""" Create a new worker.
		"""
		workerID = uuid.uuid4().hex  # generate UUID
		kwargs['id'] = workerID

		# Create worker folder and data file
		workerdir = os.path.join(self.db_workers, workerID)
		oswrapper.createDir(workerdir)
		datafile = os.path.join(workerdir, 'workerinfo.json')
		with open(datafile, 'w') as f:
			json.dump(kwargs, f, indent=4)


	def getWorkers(self):
		""" Read workers.
		"""
		workers = []
		path = '%s/*/workerinfo.json' %self.db_workers
		for filename in glob.glob(path):
			with open(filename, 'r') as f:
				try:
					workers.append(json.load(f))
				except json.decoder.JSONDecodeError:
					print("Error reading worker: " + filename)
		return workers


	def deleteWorker(self, workerID):
		""" Delete a worker from the database.
		"""
		path = os.path.join(self.db_workers, workerID)
		oswrapper.recurseRemove(path)
		return True


	def getWorkerStatus(self, workerID):
		""" Get the status of the specified worker.
		"""
		datafile = os.path.join(self.db_workers, workerID, 'workerinfo.json')
		with open(datafile, 'r') as f:
			worker = json.load(f)
		return worker['status']


	def setWorkerStatus(self, workerID, status):
		""" Set the status of the specified worker.
		"""
		datafile = os.path.join(self.db_workers, workerID, 'workerinfo.json')
		with open(datafile, 'r') as f:
			worker = json.load(f)
		if worker['status'] != status:
			worker['status'] = status
			print(worker['status'])
			with open(datafile, 'w') as f:
				json.dump(worker, f, indent=4)

