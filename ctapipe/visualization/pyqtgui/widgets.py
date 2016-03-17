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
        self.telescope_widgets = {}
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
        self.central_widget.setCurrentWidget(self.telescope_widgets[telid])

    def update(self, event=None):
        if event is not None:
            for i in range(self.tel_id_box.count()):
                self.tel_id_box.removeItem(i)
            self.event = event
            for telid in sorted(self.event.dl0.tels_with_data):
                if telid not in self.telescope_widgets:
                    self.telescope_widgets[telid] = CameraWidget(
                        geom=CameraGeometry.guess(*event.meta.pixel_pos[telid])
                    )
                    self.central_widget.addWidget(self.telescope_widgets[telid])

                self.telescope_widgets[telid].disp.image = event.dl0.tel[telid].adc_sums[0]
                self.tel_id_box.addItem(str(telid))

            self.central_widget.setCurrentWidget(
                self.telescope_widgets[int(self.tel_id_box.currentText())]
            )


class ArrayWidget(FigureCanvas, ArrayDisplay):
    def __init__(self, telescope_table, parent=None, width=5, height=4, dpi=100):
        FigureCanvas.__init__(self, parent, width, height, dpi)

        self.ax = self.fig.add_axes([0, 0, 1, 1])
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
        self.camera_disps = {}
        self.mpl_connect('pick_event', self.telescope_picker)

    def telescope_picker(self, event):
        t_id = event.ind[0]
        self.camera_disps[t_id] = self.camera_disps.get(
            t_id,
            CameraWidget(
                CameraGeometry.from_name('hess', 1),
                telescope='CT-{}'.format(t_id),
            )
        )
        self.camera_disps[t_id].show()
        self.camera_disps[t_id].setFocus()


class MainWindow(QtGui.QMainWindow):
    def __init__(self, eventsource, telescope_table, **kwargs):
        QtGui.QMainWindow.__init__(self, **kwargs)

        self.eventsource = eventsource
        self.current_event = next(eventsource)

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
        self.text.setText('{:6d}'.format(self.current_event.count))

        button = QtGui.QPushButton(bottom_frame)
        button.clicked.connect(self.next_event)
        button.setFocusPolicy(QtCore.Qt.NoFocus)
        button.setText('Next Event')
        layout.addWidget(button)

        self.array_view_tab = ArrayWidget(telescope_table=telescope_table)
        self.telescope_view_tab = TelescopeViewWidget(event=self.current_event)
        # self.telescope_view_tab.disp.image = self.current_event.dl0.tel[tel].adc_sums[0]
        self.pixel_view_tab = QtGui.QWidget()

        tabs.addTab(self.array_view_tab, 'Array View')
        tabs.addTab(self.telescope_view_tab, 'Telescope Data')
        tabs.addTab(self.pixel_view_tab, 'Pixel Data')

        self.setCentralWidget(tabs)

    def next_event(self):
        self.current_event = next(self.eventsource)
        self.text.setText('{:6d}'.format(self.current_event.count))
        self.telescope_view_tab.update(event=self.current_event)


    def closeEvent(self, event):

        if confirm_question('Are you sure you want to quit?', self):
            event.accept()
            QtCore.QCoreApplication.instance().quit()
        else:
            event.ignore()
