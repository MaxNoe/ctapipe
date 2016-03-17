from PyQt4 import QtCore, QtGui
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt4 import NavigationToolbar2QT
from matplotlib.figure import Figure
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib import style

from ctapipe.io import CameraGeometry
from ctapipe.visualization import CameraDisplay, ArrayDisplay
from .utils import confirm_question

from IPython import embed

style.use('ggplot')


class FigureCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvasQTAgg.__init__(self, self.fig)

        self.setParent(parent)
        FigureCanvas.setSizePolicy(
            self,
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding,
        )
        FigureCanvas.updateGeometry(self)


class FigureWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.canvas = FigureCanvas(parent=self)
        self.fig = self.canvas.fig

        self.topframe = QtGui.QFrame(parent=self)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(NavigationToolbar2QT(self.canvas, parent=self.topframe))
        self.topframe.setLayout(hbox)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.topframe)
        vbox.addWidget(self.canvas)
        self.setLayout(vbox)


class CameraWidget(FigureWidget):
    def __init__(self,
                 geom,
                 parent=None,
                 dpi=100,
                 **kwargs
                 ):

        FigureWidget.__init__(self, parent=parent)
        self.ax = self.fig.add_subplot(1, 1, 1)
        divider = make_axes_locatable(self.ax)
        self.cax = divider.append_axes("right", size="5%", pad=0.05)

        self.disp = CameraDisplay(geom, ax=self.ax)
        self.disp.add_colorbar(cax=self.cax)

        self.cmaps = QtGui.QComboBox()
        self.cmaps.addItems(['viridis', 'inferno', 'afmhot', 'rainbow'])
        self.cmaps.currentIndexChanged.connect(self.cmap_change)
        self.cmaps.setCurrentIndex(0)
        self.cmap_change(0)

        layout = self.topframe.layout()
        layout.addWidget(self.cmaps)

    def cmap_change(self, index):

        cmap = self.cmaps.itemText(index)
        self.disp.cmap = cmap
        self.disp.update()


class TelescopeViewWidget(QtGui.QWidget):
    def __init__(self, parent=None, event=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.camera_widgets = {}
        self.telid2camid = {}
        self.event = None

        topframe = QtGui.QFrame(parent=self)
        hbox = QtGui.QHBoxLayout()
        self.tel_id_box = QtGui.QComboBox(parent=topframe)
        self.tel_id_box.currentIndexChanged.connect(self.telescope_change)
        hbox.addWidget(self.tel_id_box)
        topframe.setLayout(hbox)

        self.central_widget = QtGui.QStackedWidget(parent=self)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(topframe)
        vbox.addWidget(self.central_widget)
        self.setLayout(vbox)

        self.update(event=event)

    def telescope_change(self, index=None):
        telid = int(self.tel_id_box.itemText(index))
        cam_id = self.telid2camid[telid]
        self.central_widget.setCurrentWidget(self.camera_widgets[cam_id])

    def update(self, event=None):
        if event is not None:
            self.event = event
            for i in range(self.tel_id_box.count()):
                self.tel_id_box.removeItem(i)
            self.event = event
            for telid in sorted(self.event.dl0.tels_with_data):
                if telid not in self.telid2camid:
                    geom = CameraGeometry.guess(*event.meta.pixel_pos[telid])
                    self.telid2camid[telid] = geom.cam_id

                    if geom.cam_id not in self.camera_widgets:
                        self.camera_widgets[geom.cam_id] = CameraWidget(geom)
                        self.central_widget.addWidget(self.camera_widgets[geom.cam_id])

                cam_id = self.telid2camid[telid]
                self.camera_widgets[cam_id].disp.image = event.dl0.tel[telid].adc_sums[0]
                self.tel_id_box.addItem(str(telid))

            self.central_widget.setCurrentWidget(
                self.camera_widgets[self.telid2camid[int(self.tel_id_box.currentText())]]
            )


class ArrayWidget(FigureCanvas, ArrayDisplay):
    def __init__(self, telescope_table, parent=None, width=5, height=4, dpi=100):
        FigureCanvas.__init__(self, parent, width, height, dpi)

        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.n_telescopes = len(telescope_table)
        ArrayDisplay.__init__(
            self,
            telescope_table['TelX'].data,
            telescope_table['TelY'].data,
            telescope_table['MirA'].data,
            ax=self.ax,
            title=False,
        )
        self.telescopes.set_cmap('viridis')
        self.telescopes.set_picker(1)
        self.ax.set_axis_off()


class MainWindow(QtGui.QMainWindow):
    def __init__(self, eventsource, telescope_table, **kwargs):
        QtGui.QMainWindow.__init__(self, **kwargs)

        self.eventsource = eventsource

        self.resize(1280, 768)
        tabs = QtGui.QTabWidget()

        bottom_frame = QtGui.QFrame()
        self.statusBar().insertWidget(0, bottom_frame)

        layout = QtGui.QHBoxLayout(bottom_frame)
        self.text = QtGui.QLineEdit(bottom_frame)
        self.text.show()
        self.text.setReadOnly(True)
        self.text.setFocusPolicy(QtCore.Qt.NoFocus)
        layout.addWidget(self.text)

        button = QtGui.QPushButton(bottom_frame)
        button.clicked.connect(self.next_event)
        button.setFocusPolicy(QtCore.Qt.NoFocus)
        button.setText('Next Event')
        layout.addWidget(button)

        self.array_view_tab = ArrayWidget(telescope_table=telescope_table)
        self.telescope_view_tab = TelescopeViewWidget()
        # self.telescope_view_tab.disp.image = self.current_event.dl0.tel[tel].adc_sums[0]
        self.pixel_view_tab = QtGui.QWidget()

        tabs.addTab(self.array_view_tab, 'Array View')
        tabs.addTab(self.telescope_view_tab, 'Telescope Data')
        tabs.addTab(self.pixel_view_tab, 'Pixel Data')

        self.setCentralWidget(tabs)
        self.next_event()

    def next_event(self):
        try:
            self.current_event = next(self.eventsource)
        except StopIteration:
            self.text.setText('Finished')
        else:
            self.text.setText('{:6d}'.format(self.current_event.count))
            self.telescope_view_tab.update(event=self.current_event)

            values = self.array_view_tab.values
            values[:] = 0
            values[list(self.current_event.dl0.tels_with_data)] = 1
            self.array_view_tab.telescopes.set_clim(0, 1)
            self.array_view_tab.values = values


    def closeEvent(self, event):

        if confirm_question('Are you sure you want to quit?', self):
            event.accept()
            QtCore.QCoreApplication.instance().quit()
        else:
            event.ignore()
