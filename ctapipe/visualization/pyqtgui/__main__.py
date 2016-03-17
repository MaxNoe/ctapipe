import sys
import signal

from PyQt4 import QtGui
from PyQt4 import QtCore

from argparse import ArgumentParser

from .widgets import MainWindow
from ctapipe.instrument.InstrumentDescription import load_hessio
from ctapipe.io.hessio import hessio_event_source

from IPython import embed

from copy import deepcopy


def sigint_handler(*args):
    sys.stderr.write('\rReceived SIGINT, terminating\n')
    QtGui.QApplication.instance().quit()


def main():

    parser = ArgumentParser()
    parser.add_argument('inputfile', metavar='inputfile', type=str)

    args = parser.parse_args()
    print(args.inputfile)

    if args.inputfile.endswith('simtel.gz'):
        source = hessio_event_source(args.inputfile)
        events = [deepcopy(next(source)) for i in range(10)]
        telescopes, cameras, optics = load_hessio(args.inputfile)
    else:
        raise ValueError('Only EventIO for the moment')

    qApp = QtGui.QApplication(sys.argv)
    signal.signal(signal.SIGINT, sigint_handler)

    widget = MainWindow(
        eventsource=iter(events),
        telescope_table=list(telescopes.values())[0],
    )
    widget.show()

    # let the QApplication process signals from the python thread
    # see http://stackoverflow.com/a/4939113/3838691
    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    sys.exit(qApp.exec_())


if __name__ == '__main__':
    main()
