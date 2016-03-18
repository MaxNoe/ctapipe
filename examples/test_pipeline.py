import logging

from ctapipe.utils.datasets import get_example_simtelarray_file

from ctapipe.io.hessio import HessioSource
from ctapipe.core.pipeline import (
    Pipeline,
    Print,
    Delay,
    Filter,
)

logging.basicConfig(level=logging.DEBUG)


pipeline = Pipeline(
    source=HessioSource(url=get_example_simtelarray_file()),
    operators=[
        Filter(lambda event: event.count != 5),
        Print(key='count'),
        Delay(delay=1),
    ],
)

pipeline.run()
