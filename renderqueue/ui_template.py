#!/usr/bin/python

# ui_template.py
#
# Mike Bonnington <mjbonnington@gmail.com>
# (c) 2018-2019
#
# UI Template - a custom class to act as a template for all windows and
# dialogs.
# This module provides windowing / UI helper functions for better integration
# of PySide / PyQt UIs in supported DCC applications.
# Currently only Maya and Nuke are supported.


import json
import os
import platform
import re
import sys

from Qt import QtCompat, QtCore, QtGui, QtSvg, QtWidgets, __binding__, __binding_version__
import rsc_rc  # Import resource file as generated by pyside-rcc

# Import custom modules
#import osOps


# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

# The vendor string must be set in order to store window geometry
VENDOR = "UNIT"


# ----------------------------------------------------------------------------
# Settings data class
# ----------------------------------------------------------------------------

class SettingsData(object):
	def __init__(self, prefs_file):
		self.prefs_file = prefs_file
		self.prefs_dict = {}

	def read(self):
		try:
			with open(self.prefs_file, 'r') as f:
				self.prefs_dict = json.load(f)
		except:
			pass

	def write(self):
		try:
			with open(self.prefs_file, 'w') as f:
				json.dump(self.prefs_dict, f, indent=4)
			return True
		except:
			return False

	def getValue(self, category, attr, default=None):
		try:
			key = "%s.%s" %(category, attr)
			return self.prefs_dict[key]
		except KeyError:
			if default is not None:
				self.prefs_dict[key] = default  # Store default value
				return default
			else:
				return None

	def setValue(self, category, attr, value):
		key = "%s.%s" %(category, attr)
		self.prefs_dict[key] = value

# ----------------------------------------------------------------------------
# End of settings data class
# ============================================================================
# Main window class
# ----------------------------------------------------------------------------

class TemplateUI(object):
	""" Template UI class.

		Subclasses derived from this class need to also inherit QMainWindow or
		QDialog. This class has no __init__ constructor as a fudge to get
		around the idiosyncracies of multiple inheritance whilst retaining
		compatibility with both Python 2 and 3.
	"""
	#def setupUI(self, **cfg):
	def setupUI(self, 
				window_object, 
				window_title="", 
				ui_file="", 
				stylesheet="", 
				prefs_file=None, 
				store_window_geometry=True):
		""" Setup the UI.
		"""
		# Define some global variables
		self.currentAttrStr = ""

		# Instantiate preferences data file
		self.prefs = SettingsData(prefs_file)
		if prefs_file:
			self.prefs.read()

		# Load UI file
		self.ui = QtCompat.loadUi(self.checkFilePath(ui_file), self)

		# Store some system UI colours & define colour palette
		tmpWidget = QtWidgets.QWidget()
		self.col = {}
		self.col['sys-window'] = tmpWidget.palette().color(QtGui.QPalette.Window)
		self.col['sys-highlight'] = tmpWidget.palette().color(QtGui.QPalette.Highlight)
		self.col['window'] = QtGui.QColor('#444444') #self.col['sys-window']
		self.col['highlight'] = QtGui.QColor('#78909c') #self.col['sys-highlight'] # load from settings
		self.computeUIPalette()

		# Load and set stylesheet
		self.stylesheet = self.checkFilePath(stylesheet)
		self.loadStyleSheet()

		# Set window title
		self.setObjectName(window_object)
		if window_title:
			self.setWindowTitle(window_title)
		else:
			window_title = self.windowTitle()

		# Perform custom widget setup
		self.setupWidgets(self.ui)

		# Restore window geometry and state
		self.store_window_geometry = store_window_geometry
		if self.store_window_geometry:

			# Use QSettings to store window geometry and state.
			# (Restore state may cause issues with PyQt5)
			#if os.environ['IC_ENV'] == 'STANDALONE':
			print("Restoring window geometry for '%s'." %self.objectName())
			try:
				self.settings = QtCore.QSettings(VENDOR, window_title)
				self.restoreGeometry(self.settings.value("geometry", ""))
				# self.restoreState(self.settings.value("windowState", ""))
			except:
				pass

			# # Makes Maya perform magic which makes the window stay on top in
			# # OS X and Linux. As an added bonus, it'll make Maya remember the
			# # window position.
			# elif os.environ['IC_ENV'] == 'MAYA':
			# 	self.setProperty("saveWindowPref", True)

			# elif os.environ['IC_ENV'] == 'NUKE':
			# 	pass

		# else:
		# 	# Move to centre of active screen
		# 	desktop = QtWidgets.QApplication.desktop()
		# 	screen = desktop.screenNumber(desktop.cursor().pos())
		# 	self.move(desktop.screenGeometry(screen).center() - self.frameGeometry().center())
		# 	# Move to centre of parent window
		# 	self.move(self.parent.frameGeometry().center() - self.frameGeometry().center())

		# Set up keyboard shortcuts
		self.shortcutReloadStyleSheet = QtWidgets.QShortcut(self)
		self.shortcutReloadStyleSheet.setKey('Ctrl+Shift+R')
		self.shortcutReloadStyleSheet.activated.connect(self.loadStyleSheet)


	def getInfo(self):
		""" Return some version info about Python, Qt, binding, etc.
		"""
		info = {}
		info['Python'] = "%d.%d.%d" %(sys.version_info[0], sys.version_info[1], sys.version_info[2])
		info[__binding__] = __binding_version__
		info['Qt'] = QtCore.qVersion()
		info['OS'] = platform.system()
		info['Environment'] = ENVIRONMENT

		return info
		# print("Window object: %s Parent: %s" %(self, self.parent))


	def promptDialog(self, message, title="Message", conf=False, modal=True):
		""" Opens a message box dialog.
		"""
		msgBox = QtWidgets.QMessageBox(parent=self)
		msgBox.setWindowTitle(title)
		msgBox.setText(title)
		msgBox.setInformativeText(message)
		if conf:
			msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
		else:
			msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
		msgBox.setDefaultButton(QtWidgets.QMessageBox.Ok);
		return msgBox.exec_()


	def fileDialog(self, startingDir, fileFilter='All files (*.*)'):
		""" Opens a dialog from which to select a single file.

			The env check puts the main window in the background so dialog pop
			up can return properly when running inside certain applications.
			The window flags bypass a Mac bug that made the dialog always
			appear under the Icarus window. This is ignored in a Linux env.
			(currently disabled).
		"""
		# envOverride = ['MAYA', 'NUKE']
		# if os.environ.get('IC_ENV', "STANDALONE") in envOverride:
		# 	if os.environ['IC_RUNNING_OS'] == "MacOS":
		# 		self.setWindowFlags(QtCore.Qt.WindowStaysOnBottomHint | QtCore.Qt.X11BypassWindowManagerHint | QtCore.Qt.WindowCloseButtonHint)
		# 		self.show()
		# 	dialog = QtWidgets.QFileDialog.getOpenFileName(self, self.tr('Files'), startingDir, fileFilter)
		# 	if os.environ['IC_RUNNING_OS'] == "MacOS":
		# 		self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.X11BypassWindowManagerHint | QtCore.Qt.WindowCloseButtonHint)
		# 		self.show()
		# else:
		dialog = QtWidgets.QFileDialog.getOpenFileName(self, self.tr('Files'), startingDir, fileFilter)

		try:
			return dialog[0]
		except IndexError:
			return None


	def folderDialog(self, startingDir):
		""" Opens a dialog from which to select a folder.
		"""
		dialog = QtWidgets.QFileDialog.getExistingDirectory(self, self.tr('Directory'), startingDir, QtWidgets.QFileDialog.DontResolveSymlinks | QtWidgets.QFileDialog.ShowDirsOnly)

		return dialog


	def colorPickerDialog(self, current_color=None):
		""" Opens a system dialog for choosing a colour.
			Return the selected colour as a QColor object, or None if the
			dialog is cancelled.
		"""
		color_dialog = QtWidgets.QColorDialog()
		#color_dialog.setOption(QtWidgets.QColorDialog.DontUseNativeDialog)

		# Set current colour
		if current_color is not None:
			color_dialog.setCurrentColor(current_color)

		# Only return a color if valid / dialog accepted
		if color_dialog.exec_() == color_dialog.Accepted:
			color = color_dialog.selectedColor()
			return color


	# ------------------------------------------------------------------------
	# Widget handlers

	def setupWidgets(self, 
		             parentObject, 
		             forceCategory=None, 
		             inherit=None, 
		             storeProperties=True, 
		             updateOnly=False):
		""" Set up all the child widgets of the specified parent object.

			If 'forceCategory' is specified, this will override the category
			of all child widgets.
			'inherit' specifies an alternative XML data source for widgets
			to get their values from.
			If 'storeProperties' is True, the values will be stored in the XML
			data as well as applied to the widgets.
			If 'updateOnly' is True, only the widgets' values will be updated.
		"""
		if forceCategory is not None:
			category = forceCategory

		if updateOnly:
			storeProperties = False

		for widget in parentObject.findChildren(QtWidgets.QWidget):

			# Enable expansion of custom rollout group box controls...
			if widget.property('expandable'):
				if isinstance(widget, QtWidgets.QGroupBox):
					widget.setCheckable(True)
					# widget.setChecked(expand)
					widget.setFixedHeight(widget.sizeHint().height())
					if not updateOnly:
						widget.toggled.connect(self.toggleExpandGroup)

			# # Enable colour chooser buttons...
			# if widget.property('colorChooser'):
			# 	if isinstance(widget, QtWidgets.QToolButton):
			# 		if not updateOnly:
			# 			widget.clicked.connect(self.storeColor)

			# Set up handler for push buttons...
			if widget.property('exec'):
				if isinstance(widget, QtWidgets.QPushButton):
					if not updateOnly:
						widget.clicked.connect(self.execPushButton)

			# Set up handlers for different widget types & apply values
			attr = widget.property('xmlTag')
			if attr:
				self.base_widget = widget.objectName()
				if forceCategory is None:
					category = self.findCategory(widget)
				if category:
					widget.setProperty('xmlCategory', category)

					if inherit is None:
						value = self.prefs.getValue(category, attr)
					else:
						value = self.prefs.getValue(category, attr)
						if value is None:
							value = inherit.getValue(category, attr)

							# widget.setProperty('xmlTag', None)
							widget.setProperty('inheritedValue', True)
							widget.setToolTip("This value is being inherited. Change the value to override the inherited value.")  # Rework this in case widgets already have a tooltip

							# Apply pop-up menu to remove override - can't get to work here
							# self.addContextMenu(widget, "Remove override", self.removeOverrides)
							# widget.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

							# actionRemoveOverride = QtWidgets.QAction("Remove override", None)
							# actionRemoveOverride.triggered.connect(self.removeOverrides)
							# widget.addAction(actionRemoveOverride)


					# Sliders...
					if isinstance(widget, QtWidgets.QSlider):
						if value is not None:
							widget.setValue(int(value))
						if storeProperties:
							self.storeValue(category, attr, widget.value())
						if not updateOnly:
							widget.valueChanged.connect(self.storeSliderValue)

					# Spin boxes...
					if isinstance(widget, QtWidgets.QSpinBox):
						if value is not None:
							widget.setValue(int(value))
						if storeProperties:
							self.storeValue(category, attr, widget.value())
						if not updateOnly:
							widget.valueChanged.connect(self.storeSpinBoxValue)

					# Double spin boxes...
					elif isinstance(widget, QtWidgets.QDoubleSpinBox):
						if value is not None:
							widget.setValue(float(value))
						if storeProperties:
							self.storeValue(category, attr, widget.value())
						if not updateOnly:
							widget.valueChanged.connect(self.storeSpinBoxValue)

					# Line edits...
					elif isinstance(widget, QtWidgets.QLineEdit):
						if value is not None:
							widget.setText(value)
						if storeProperties:
							self.storeValue(category, attr, widget.text())
						if not updateOnly:
							# widget.textEdited.connect(self.storeLineEditValue)
							widget.textChanged.connect(self.storeLineEditValue)

					# Plain text edits...
					elif isinstance(widget, QtWidgets.QPlainTextEdit):
						if value is not None:
							widget.setPlainText(value)
						if storeProperties:
							self.storeValue(category, attr, widget.toPlainText())
						if not updateOnly:
							widget.textChanged.connect(self.storeTextEditValue)

					# Check boxes...
					elif isinstance(widget, QtWidgets.QCheckBox):
						if value is not None:
							if value == True:
								widget.setCheckState(QtCore.Qt.Checked)
							elif value == False:
								widget.setCheckState(QtCore.Qt.Unchecked)
						if storeProperties:
							self.storeValue(category, attr, self.getCheckBoxValue(widget))
						if not updateOnly:
							widget.toggled.connect(self.storeCheckBoxValue)

					# Radio buttons...
					elif isinstance(widget, QtWidgets.QRadioButton):
						if value is not None:
							widget.setAutoExclusive(False)
							if value == widget.text():
								widget.setChecked(True)
							else:
								widget.setChecked(False)
							widget.setAutoExclusive(True)
						if storeProperties:
							if widget.isChecked():
								self.storeValue(category, attr, widget.text())
						if not updateOnly:
							widget.toggled.connect(self.storeRadioButtonValue)

					# Combo boxes...
					elif isinstance(widget, QtWidgets.QComboBox):
						if value is not None:
							if widget.findText(value) == -1:
								widget.addItem(value)
							widget.setCurrentIndex(widget.findText(value))
						if storeProperties:
							self.storeValue(category, attr, widget.currentText())
						if not updateOnly:
							if widget.isEditable():
								widget.editTextChanged.connect(self.storeComboBoxValue)
							else:
								widget.currentIndexChanged.connect(self.storeComboBoxValue)

					# Enable colour chooser buttons...
					elif isinstance(widget, QtWidgets.QToolButton):
						if widget.property('colorChooser'):
							if value is not None:
								widget.setStyleSheet("QWidget { background-color: %s }" %value)
							# if storeProperties:
							# 	self.storeValue(category, attr, widget.currentText())
							if not updateOnly:
								widget.clicked.connect(self.storeColor)


	def findCategory(self, widget):
		""" Recursively check the parents of the given widget until a custom
			property 'xmlCategory' is found.
		"""
		if widget.property('xmlCategory'):
			#print("Category '%s' found for '%s'." %(widget.property('xmlCategory'), widget.objectName()))
			return widget.property('xmlCategory')
		else:
			# Stop iterating if the widget's parent in the main window...
			if isinstance(widget.parent(), QtWidgets.QMainWindow):
				#print("No category could be found for '%s'. The widget's value cannot be stored." %self.base_widget)
				return None
			else:
				return self.findCategory(widget.parent())


	def addContextMenu(self, widget, name, command, icon=None):
		""" Add context menu item to widget.

			'widget' should be a Push Button or Tool Button.
			'name' is the text to be displayed in the menu.
			'command' is the function to run when the item is triggered.
			'icon' is a pixmap to use for the item's icon (optional).
		"""
		widget.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
		actionName = "action%s" %re.sub(r"[^\w]", "_", name)

		action = QtWidgets.QAction(name, None)
		if icon:
			actionIcon = QtGui.QIcon()
			#actionIcon.addPixmap(QtGui.QPixmap(osOps.absolutePath("$IC_FORMSDIR/rsc/%s.png" %icon)), QtGui.QIcon.Normal, QtGui.QIcon.Off)
			#actionIcon.addPixmap(QtGui.QPixmap(osOps.absolutePath("$IC_FORMSDIR/rsc/%s_disabled.png" %icon)), QtGui.QIcon.Disabled, QtGui.QIcon.Off)
			searchpath = [pipeline.iconsdir, pipeline.formsdir]
			actionIcon.addPixmap(QtGui.QPixmap(self.checkFilePath(icon+".png", searchpath)), QtGui.QIcon.Normal, QtGui.QIcon.Off)
			actionIcon.addPixmap(QtGui.QPixmap(self.checkFilePath(icon+"_disabled.png", searchpath)), QtGui.QIcon.Disabled, QtGui.QIcon.Off)
			action.setIcon(actionIcon)
		action.setObjectName(actionName)
		action.triggered.connect(command)
		widget.addAction(action)

		# Make a class-scope reference to this object
		# (won't work without it for some reason)
		exec_str = "self.%s = action" %actionName
		exec(exec_str)


	def setSVGIcon(self, icon_name):
		""" 
		"""
		w, h = 64, 64
		svg_renderer = QtSvg.QSvgRenderer('icons/%s.svg' %icon_name)
		image = QtGui.QImage(w, h, QtGui.QImage.Format_ARGB32)
		# Set the ARGB to 0 to prevent rendering artifacts
		image.fill(0x00000000)
		svg_renderer.render(QtGui.QPainter(image))
		pixmap = QtGui.QPixmap.fromImage(image)
		icon = QtGui.QIcon(pixmap)
		#widget.setIcon(icon)
		#widget.setSizeHint(1, QtCore.QSize(w, h))

		# effect = QtWidgets.QGraphicsColorizeEffect(self)
		# effect.setColor(QtGui.QColor('#ffffff'))
		# #effect.setStrength(0.6)
		# pixmap.setGraphicsEffect(effect)

		# painter = QtGui.QPainter(temp)
		# painter.setCompositionMode(painter.CompositionMode_Overlay)
		# painter.fillRect(temp.rect(), color)
		# painter.end()
		# self.tinted.setPixmap(temp)

		return icon


	def toggleExpertWidgets(self, isExpertMode, parentObject):
		""" Show/hide all widgets with the custom property 'expert' under
			the specified parentObject.
		"""
		types = (
			QtWidgets.QMenu, 
			QtWidgets.QMenuBar, 
			QtWidgets.QAction, 
			)

		try:
			for item in parentObject.findChildren(types):
				if item.property('expert'):
					item.setVisible(isExpertMode)

		# Fix for Qt4 where findChildren signature doesn't suport a tuple for
		# an argument...
		except TypeError:
			expert_items = []
			for widget_type in types:
				for item in parentObject.findChildren(widget_type):
					if item.property('expert'):
						expert_items.append(item)
			for item in expert_items:
				item.setVisible(isExpertMode)


	def conformFormLayoutLabels(self, parentObject, padding=8):
		""" Conform the widths of all labels in formLayouts under the
			specified parentObject for a more coherent appearance.

			'padding' is an amount in pixels to add to the max width.
		"""
		labels = []
		labelWidths = []

		# Find all labels in form layouts
		for layout in parentObject.findChildren(QtWidgets.QFormLayout):
			# print(layout.objectName())
			items = (layout.itemAt(i) for i in range(layout.count()))
			for item in items:
				widget = item.widget()
				if isinstance(widget, QtWidgets.QLabel):
					labels.append(widget)

		# Find labels in first column of grid layouts
		for layout in parentObject.findChildren(QtWidgets.QGridLayout):
			# print(layout.objectName())
			items = (layout.itemAt(i) for i in range(layout.count()))
			for item in items:
				widget = item.widget()
				if isinstance(widget, QtWidgets.QLabel):
					# Only items in first column (there's probably a neater
					# way to do this)
					if layout.getItemPosition(layout.indexOf(widget))[1] == 0:
						labels.append(widget)

		# Find label widths
		for label in labels:
			fontMetrics = QtGui.QFontMetrics(label.font())
			width = fontMetrics.width(label.text())
			#print('Width of "%s": %d px' %(label.text(), width))
			labelWidths.append(width)

		# Get widest label & set all labels widths to match
		if labelWidths:
			maxWidth = max(labelWidths)
			#print("Max label width : %d px (%d inc padding)" %(maxWidth, maxWidth+padding))
			for label in labels:
				label.setFixedWidth(maxWidth+padding)
				label.setAlignment(QtCore.Qt.AlignVCenter|QtCore.Qt.AlignRight)


	def getCheckBoxValue(self, checkBox):
		""" Get the value from a checkbox and return a Boolean value.
		"""
		if checkBox.checkState() == QtCore.Qt.Checked:
			return True
		else:
			return False


	def getWidgetMeta(self, widget):
		""" 
		"""
		widget.setProperty('inheritedValue', False)
		widget.setToolTip("")  # Rework this in case widgets already have a tooltip
		widget.style().unpolish(widget)
		widget.style().polish(widget)

		category = widget.property('xmlCategory')
		attr = widget.property('xmlTag')
		return category, attr


	# @QtCore.Slot()
	def execPushButton(self):
		""" Execute the function associated with a button.
			***NOT YET IMPLEMENTED***
		"""
		print("%s %s" %(self.sender().objectName(), self.sender().property('exec')))


	# @QtCore.Slot()
	def storeColor(self):
		""" Get the colour from a dialog opened from a colour chooser button.
		"""
		widget = self.sender()

		# Get current colour and pass to function
		current_color = widget.palette().color(QtGui.QPalette.Background)
		color = self.colorPickerDialog(current_color)
		if color:
			widget.setStyleSheet("QWidget { background-color: %s }" %color.name())
			# category = self.sender().property('xmlCategory')
			# attr = self.sender().property('xmlTag')
			category, attr = self.getWidgetMeta(self.sender())
			self.storeValue(category, attr, color.name())


	# @QtCore.Slot()
	def storeSliderValue(self):
		""" Get the value from a Slider and store in XML data.
		"""
		# category = self.sender().property('xmlCategory')
		# attr = self.sender().property('xmlTag')
		category, attr = self.getWidgetMeta(self.sender())
		value = self.sender().value()
		self.storeValue(category, attr, value)


	# @QtCore.Slot()
	def storeSpinBoxValue(self):
		""" Get the value from a Spin Box and store in XML data.
		"""
		# category = self.sender().property('xmlCategory')
		# attr = self.sender().property('xmlTag')
		category, attr = self.getWidgetMeta(self.sender())
		value = self.sender().value()
		self.storeValue(category, attr, value)


	# @QtCore.Slot()
	def storeLineEditValue(self):
		""" Get the value from a Line Edit and store in XML data.
		"""
		# category = self.sender().property('xmlCategory')
		# attr = self.sender().property('xmlTag')
		category, attr = self.getWidgetMeta(self.sender())
		value = self.sender().text()
		self.storeValue(category, attr, value)


	# @QtCore.Slot()
	def storeTextEditValue(self):
		""" Get the value from a Plain Text Edit and store in XML data.
		"""
		# category = self.sender().property('xmlCategory')
		# attr = self.sender().property('xmlTag')
		category, attr = self.getWidgetMeta(self.sender())
		value = self.sender().toPlainText()
		self.storeValue(category, attr, value)


	# @QtCore.Slot()
	def storeCheckBoxValue(self):
		""" Get the value from a Check Box and store in XML data.
		"""
		# category = self.sender().property('xmlCategory')
		# attr = self.sender().property('xmlTag')
		category, attr = self.getWidgetMeta(self.sender())
		value = self.getCheckBoxValue(self.sender())
		self.storeValue(category, attr, value)


	# @QtCore.Slot()
	def storeRadioButtonValue(self):
		""" Get the value from a Radio Button group and store in XML data.
		"""
		if self.sender().isChecked():
			# category = self.sender().property('xmlCategory')
			# attr = self.sender().property('xmlTag')
			category, attr = self.getWidgetMeta(self.sender())
			value = self.sender().text()
			self.storeValue(category, attr, value)


	# @QtCore.Slot()
	def storeComboBoxValue(self):
		""" Get the value from a Combo Box and store in XML data.
		"""
		# category = self.sender().property('xmlCategory')
		# attr = self.sender().property('xmlTag')
		category, attr = self.getWidgetMeta(self.sender())
		value = self.sender().currentText()
		self.storeValue(category, attr, value)


	def storeValue(self, category, attr, value=""):
		""" Store value in XML data.
		"""
		currentAttrStr = "%20s %s.%s" %(type(value), category, attr)
		# if currentAttrStr == self.currentAttrStr:
		# 	print("%s=%s" %(currentAttrStr, value), inline=True)
		# else:
		# 	print("%s=%s" %(currentAttrStr, value))
		#print("%s=%s" %(currentAttrStr, value))
		self.prefs.setValue(category, attr, value)
		self.currentAttrStr = currentAttrStr


	# @QtCore.Slot()
	def toggleExpandGroup(self):
		""" Toggle expansion of custom rollout group box control.
		"""
		groupBox = self.sender()
		state = groupBox.isChecked()
		if state:
			groupBox.setFixedHeight(groupBox.sizeHint().height())
		else:
			groupBox.setFixedHeight(20)  # Slightly hacky - needs to match value defined in QSS

		#self.setFixedHeight(self.sizeHint().height())  # Resize window


	def populateComboBox(self, comboBox, contents, replace=True, addEmptyItems=False):
		""" Use a list (contents) to populate a combo box.
			If 'replace' is true, the existing items will be replaced,
			otherwise the contents will be appended to the existing items.
		"""
		# Store current value
		current = comboBox.currentText()

		# Clear menu
		if replace:
			comboBox.clear()

		# Populate menu
		if contents:
			for item in contents:
				if addEmptyItems:
					comboBox.addItem(item)
				else:
					if item:
						comboBox.addItem(item)

		# Set to current value
		index = comboBox.findText(current)
		if index == -1:
			comboBox.setCurrentIndex(0)
		else:
			comboBox.setCurrentIndex(index)

	# End widget handlers
	# ------------------------------------------------------------------------


	def checkFilePath(self, filename, searchpath=[]):
		""" Check if 'filename' exists. If not, search through list of folders
			given in the optional searchpath, then check in the current dir.
		"""
		if os.path.isfile(filename):
			return filename
		else:
			# Append current dir to searchpath and try each in turn
			searchpath.append(os.path.dirname(__file__))
			for folder in searchpath:
				filepath = os.path.join(searchpath, filename)
				if os.path.isfile(filepath):
					return filepath

			# File not found
			return None


	def loadStyleSheet(self):
		""" Load/reload stylesheet.
		"""
		if self.stylesheet:
			with open(self.stylesheet, 'r') as fh:
				stylesheet = fh.read()

			# Read predefined colour variables and apply them to the style
			for key, value in self.col.items():
				rgb = "%d, %d, %d" %(value.red(), value.green(), value.blue())
				stylesheet = stylesheet.replace("%"+key+"%", rgb)

			self.setStyleSheet(stylesheet)
			return stylesheet


	def saveStyleSheet(self):
		""" Save stylesheet.
		"""
		stylesheet = self.loadStyleSheet()

		with open('style_out.qss', 'w') as fh:
			fh.write("/* Generated by uistyle */\n")
			fh.write(stylesheet)


	def unloadStyleSheet(self):
		""" Load/reload stylesheet.
		"""
		self.setStyleSheet("")


	def offsetColor(self, input_color, amount, clamp=None):
		""" Offset input_color by a given amount. Only works in greyscale.
		"""
		if amount == 0:  # Do nothing
			return input_color

		elif amount > 0:  # Lighten
			if clamp is None:
				min_clamp = 0
			else:
				min_clamp = clamp
			max_clamp = 255

		elif amount < 0:  # Darken
			min_clamp = 0
			if clamp is None:
				max_clamp = 255
			else:
				max_clamp = clamp

		lum = max(min_clamp, min(input_color.lightness()+amount, max_clamp))
		return QtGui.QColor(lum, lum, lum)


	def computeUIPalette(self):
		""" Compute UI colours based on window colour.
		"""
		#self.col['text'] = QtGui.QColor(204, 204, 204)
		self.col['disabled'] = QtGui.QColor(102, 102, 102)
		#self.col['base'] = QtGui.QColor(34, 34, 34)
		#self.col['button'] = QtGui.QColor(102, 102, 102)
		#self.col['hover'] = QtGui.QColor(119, 119, 119)
		#self.col['pressed'] = QtGui.QColor(60, 60, 60)
		self.col['pressed'] = self.col['highlight']
		#self.col['checked'] = QtGui.QColor(51, 51, 51)
		#self.col['menu-bg'] = QtGui.QColor(51, 51, 51)
		#self.col['menu-border'] = QtGui.QColor(68, 68, 68)
		self.col['group-bg'] = QtGui.QColor(128, 128, 128)
		self.col['line'] = self.col['window'].darker(110)
		#self.col['highlighted-text'] = QtGui.QColor(255, 255, 255)
		self.col['mandatory'] = QtGui.QColor('#f92672')
		self.col['warning'] = QtGui.QColor('#e6db74')
		self.col['inherited'] = QtGui.QColor('#a1efe4')

		if self.col['window'].lightness() < 128:  # Dark UI
			self.col['text'] = self.offsetColor(self.col['window'], +68, 204)
			self.col['base'] = self.offsetColor(self.col['window'], -34, 34)
			self.col['alternate'] = self.offsetColor(self.col['base'], +8)
			self.col['button'] = self.offsetColor(self.col['window'], +34, 102)
			self.col['menu-bg'] = self.offsetColor(self.col['window'], -17, 68)
			self.col['menu-border'] = self.offsetColor(self.col['menu-bg'], +17)
		else:  # Light UI
			self.col['text'] = self.offsetColor(self.col['window'], -68, 51)
			self.col['base'] = self.offsetColor(self.col['window'], +34, 221)
			self.col['alternate'] = self.offsetColor(self.col['base'], -8)
			self.col['button'] = self.offsetColor(self.col['window'], -34, 187)
			self.col['menu-bg'] = self.offsetColor(self.col['window'], +17, 187)
			self.col['menu-border'] = self.offsetColor(self.col['menu-bg'], -17)

		self.col['hover'] = self.offsetColor(self.col['button'], +17)
		self.col['checked'] = self.offsetColor(self.col['button'], -17)
		#print("hover: %s" %self.col['hover'].name())

		if self.col['highlight'].lightness() < 192:
			self.col['highlighted-text'] = QtGui.QColor(255, 255, 255)
		else:
			self.col['highlighted-text'] = QtGui.QColor(0, 0, 0)

		if self.col['button'].lightness() < 192:
			self.col['button-text'] = self.offsetColor(self.col['button'], +68, 204)
		else:
			self.col['button-text'] = self.offsetColor(self.col['button'], -68, 51)

		self.col['mandatory-bg'] = self.col['mandatory']
		if self.col['mandatory-bg'].lightness() < 128:
			self.col['mandatory-text'] = self.offsetColor(self.col['mandatory-bg'], +68, 204)
		else:
			self.col['mandatory-text'] = self.offsetColor(self.col['mandatory-bg'], -68, 51)

		self.col['warning-bg'] = self.col['warning']
		if self.col['warning-bg'].lightness() < 128:
			self.col['warning-text'] = self.offsetColor(self.col['warning-bg'], +68, 204)
		else:
			self.col['warning-text'] = self.offsetColor(self.col['warning-bg'], -68, 51)

		self.col['inherited-bg'] = self.col['inherited']
		if self.col['inherited-bg'].lightness() < 128:
			self.col['inherited-text'] = self.offsetColor(self.col['inherited-bg'], +68, 204)
		else:
			self.col['inherited-text'] = self.offsetColor(self.col['inherited-bg'], -68, 51)


	# @QtCore.Slot()
	def setUIBrightness(self, value):
		""" Set the UI style background shade.
		"""
		#print(value)
		self.col['window'] = QtGui.QColor(value, value, value)
		self.computeUIPalette()
		self.loadStyleSheet()


	# @QtCore.Slot()
	def setAccentColor(self, color=None):
		""" Set the UI style accent colour.
		"""
		widget = self.sender()

		# Get current colour and pass to function
		current_color = widget.palette().color(QtGui.QPalette.Background)
		color = self.colorPickerDialog(current_color)
		if color:
			widget.setStyleSheet("QWidget { background-color: %s }" %color.name())
			self.col['highlight'] = color
			self.computeUIPalette()
			self.loadStyleSheet()
		# self.col['highlight'] = widget.palette().color(QtGui.QPalette.Background)
		# self.computeUIPalette()
		# self.loadStyleSheet()


	def storeWindow(self):
		""" Store window geometry and state.
			(Save state may cause issues with PyQt5)
		"""
		#if ENVIRONMENT == 'STANDALONE':
		if self.store_window_geometry:
			#if os.environ['IC_ENV'] == 'STANDALONE':
			print("Storing window geometry for '%s'." %self.objectName())
			try:
				self.settings.setValue("geometry", self.saveGeometry())
				# self.settings.setValue("windowState", self.saveState())
			except:
				pass


	# def showEvent(self, event):
	# 	""" Event handler for when window is shown.
	# 	"""
	# 	pass


	# def closeEvent(self, event):
	# 	""" Event handler for when window is closed.
	# 	"""
	# 	self.storeWindow()
	# 	QtWidgets.QMainWindow.closeEvent(self, event)
	# 	#self.closeEvent(self, event)


	def save(self):
		""" Save data.
		"""
		if self.prefs.write():
			return True
		else:
			return False


	# def saveAndExit(self):
	# 	""" Save data and close window.
	# 	"""
	# 	if self.save():
	# 		self.returnValue = True
	# 		self.hide()
	# 		self.ui.hide()
	# 		#self.exit()
	# 	else:
	# 		self.exit()


	# def exit(self):
	# 	""" Exit the window with negative return value.
	# 	"""
	# 	self.storeWindow()
	# 	#self.returnValue = False
	# 	self.hide()

# ----------------------------------------------------------------------------
# End of main window class
# ============================================================================
# DCC application helper functions
# ----------------------------------------------------------------------------

def _maya_delete_ui(window_object, window_title):
	""" Delete existing UI in Maya.
	"""
	if mc.window(window_object, query=True, exists=True):
		mc.deleteUI(window_object)  # Delete window
	if mc.dockControl('MayaWindow|' + window_title, query=True, exists=True):
		mc.deleteUI('MayaWindow|' + window_title)  # Delete docked window


# def _houdini_delete_ui(window_object, window_title):
# 	""" Delete existing UI in Houdini.
# 	"""
# 	pass


def _nuke_delete_ui(window_object, window_title):
	""" Delete existing UI in Nuke.
	"""
	for obj in QtWidgets.QApplication.allWidgets():
		if obj.objectName() == window_object:
			obj.deleteLater()


def _maya_main_window():
	""" Return Maya's main window.
	"""
	for obj in QtWidgets.QApplication.topLevelWidgets():
		if obj.objectName() == 'MayaWindow':
			return obj
	raise RuntimeError("Could not find MayaWindow instance")


# def _houdini_main_window():
# 	""" Return Houdini's main window.
# 	"""
# 	return hou.qt.mainWindow()
# 	raise RuntimeError("Could not find Houdini's main window instance")


def _nuke_main_window():
	""" Returns Nuke's main window.
	"""
	for obj in QtWidgets.QApplication.topLevelWidgets():
		if (obj.inherits('QMainWindow') and obj.metaObject().className() == 'Foundry::UI::DockMainWindow'):
			return obj
	raise RuntimeError("Could not find DockMainWindow instance")


def _nuke_set_zero_margins(widget_object):
	""" Remove Nuke margins when docked UI.
		More info:
		https://gist.github.com/maty974/4739917
	"""
	parentApp = QtWidgets.QApplication.allWidgets()
	parentWidgetList = []
	for parent in parentApp:
		for child in parent.children():
			if widget_object.__class__.__name__ == child.__class__.__name__:
				parentWidgetList.append(parent.parentWidget())
				parentWidgetList.append(parent.parentWidget().parentWidget())
				parentWidgetList.append(parent.parentWidget().parentWidget().parentWidget())

				for sub in parentWidgetList:
					for tinychild in sub.children():
						try:
							tinychild.setContentsMargins(0, 0, 0, 0)
						except:
							pass



# class IconProvider(QtWidgets.QFileIconProvider):
# 	def icon(self, fileInfo):
# 		if fileInfo.isDir():
# 			return QtGui.QIcon(':/rsc/rsc/icon_folder.png') 
# 		return QtWidgets.QFileIconProvider.icon(self, fileInfo)


# ----------------------------------------------------------------------------
# Run functions
# ----------------------------------------------------------------------------

# def run_(**kwargs):
# 	# for key, value in kwargs.iteritems():
# 	# 	print "%s = %s" % (key, value)
# 	customUI = TemplateUI(**kwargs)
# 	#customUI.setAttribute( QtCore.Qt.WA_DeleteOnClose )
# 	print customUI
# 	customUI.show()
# 	#customUI.raise_()
# 	#customUI.exec_()


# def run_maya(**kwargs):
# 	""" Run in Maya.
# 	"""
# 	_maya_delete_ui()  # Delete any already existing UI
# 	customUI = TemplateUI(parent=_maya_main_window())

# 	# Makes Maya perform magic which makes the window stay on top in OS X and
# 	# Linux. As an added bonus, it'll make Maya remember the window position.
# 	customUI.setProperty("saveWindowPref", True)

# 	customUI.display(**kwargs)  # Show the UI


# def run_nuke(**kwargs):
# 	""" Run in Nuke.
# 	"""
# 	_nuke_delete_ui()  # Delete any already existing UI
# 	customUI = TemplateUI(parent=_nuke_main_window())

# 	customUI.display(**kwargs)  # Show the UI


# # Detect environment and run application
# if os.environ['IC_ENV'] == 'STANDALONE':
# 	pass
# elif os.environ['IC_ENV'] == 'MAYA':
# 	import maya.cmds as mc
# 	# run_maya()
# elif os.environ['IC_ENV'] == 'NUKE':
# 	import nuke
# 	import nukescripts
# 	# run_nuke()
# # elif __name__ == '__main__':
# # 	run_standalone()

# ----------------------------------------------------------------------------
# Environment detection
# ----------------------------------------------------------------------------

ENVIRONMENT = os.environ.get('IC_ENV', "STANDALONE")

try:
	import maya.cmds as mc
	ENVIRONMENT = "MAYA"
except ImportError:
	pass

try:
	import hou
	ENVIRONMENT = "HOUDINI"
except ImportError:
	pass

try:
	import nuke
	import nukescripts
	ENVIRONMENT = "NUKE"
except ImportError:
	pass
