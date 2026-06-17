import pyray as rl
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.spinner import Spinner
import time

gui_app.init_window("Spinner")
spinner = Spinner()
spinner.set_text("10") # Set 10% progress
# Step the rotation slightly to simulate it spinning
spinner._rotation = 45.0 

rl.begin_drawing()
rl.clear_background(rl.BLACK)
spinner._render(rl.Rectangle(0, 0, gui_app.width, gui_app.height))
rl.take_screenshot("spinner_screenshot.png")
rl.end_drawing()
