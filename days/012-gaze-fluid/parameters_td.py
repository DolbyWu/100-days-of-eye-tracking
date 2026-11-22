import numpy as np


def onCook(scriptOp):
    defaults = ((.5, .5, 0, .038), (0, 0, 0, 1/60), (.5, .5, 1, 0),
                (210, 95, .38, .47))
    values = scriptOp.fetch("vectors", defaults)
    scriptOp.copyNumpyArray(np.asarray([values], dtype=np.float32))
