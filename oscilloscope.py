import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets  # Updated import
import sounddevice as sd

# Audio parameters
SAMPLE_RATE = 96000  # Adjust to match your audio interface's sample rate
BUFFER_SIZE = 4096  # Number of frames per buffer

# Create the application instance
app = QtWidgets.QApplication([])  # Updated QApplication

# Retrieve the screen's refresh rate
screen = app.primaryScreen()
refresh_rate = screen.refreshRate()
if refresh_rate <= 0:
    # Default to 60Hz if unable to retrieve
    refresh_rate = 60.0
    print(f"Unable to retrieve screen refresh rate. Defaulting to {refresh_rate}Hz.")
else:
    print(f"Screen refresh rate: {refresh_rate}Hz")

# Calculate the timer interval in milliseconds
timer_interval = 1000.0 / refresh_rate
print(f"Timer interval set to: {timer_interval:.2f} ms")

# Set up the window
win = pg.GraphicsLayoutWidget(show=True, title="XY Oscilloscope")
win.resize(3024, 1964)  # 3024 x 1964
win.setWindowTitle('XY Oscilloscope')

# Add a plot area
plot = win.addPlot(title="Real-time XY Plot")
plot.setLabel('left', 'Channel 2 Amplitude')
plot.setLabel('bottom', 'Channel 1 Amplitude')
plot.setRange(xRange=[-1, 1], yRange=[-1, 1], padding=0.1)
plot.showGrid(x=True, y=True)

# Create a curve to update
curve = plot.plot(pen=None, symbol='o', symbolSize=2, symbolPen=None, symbolBrush='y')

# Audio data buffer
xdata = np.zeros(BUFFER_SIZE)
ydata = np.zeros(BUFFER_SIZE)

# Lock for thread safety
data_lock = QtCore.QMutex()

# Audio callback function
def audio_callback(indata, frames, time_info, status):
    global xdata, ydata
    if status:
        print(status, file=sys.stderr)
    with QtCore.QMutexLocker(data_lock):
        # Ensure there are at least two channels
        if indata.shape[1] < 2:
            print("Insufficient channels in audio input.", file=sys.stderr)
            return
        # Normalize audio data to fit within [-1, 1] for plotting
        x_max = np.max(np.abs(indata[:, 0]))
        y_max = np.max(np.abs(indata[:, 1]))
        xdata[:] = indata[:, 0] / x_max if x_max != 0 else indata[:, 0]
        ydata[:] = indata[:, 1] / y_max if y_max != 0 else indata[:, 1]

# Update function for the plot
def update_plot():
    global curve, xdata, ydata
    with QtCore.QMutexLocker(data_lock):
        # Optionally, downsample the data to match the display refresh rate
        # For simplicity, we'll plot the latest BUFFER_SIZE samples
        curve.setData(xdata, ydata)

# Set up a timer to refresh the plot
timer = QtCore.QTimer()
timer.timeout.connect(update_plot)
timer.start(int(timer_interval))  # Update based on screen refresh rate

# Start audio stream
stream = sd.InputStream(
    channels=2,
    samplerate=SAMPLE_RATE,
    blocksize=BUFFER_SIZE,
    callback=audio_callback
)

try:
    stream.start()
except Exception as e:
    print(f"Failed to start audio stream: {e}", file=sys.stderr)
    sys.exit(1)

# Start the application event loop
if __name__ == '__main__':
    try:
        sys.exit(app.exec())  # Updated to use exec()
    finally:
        stream.stop()
        stream.close()