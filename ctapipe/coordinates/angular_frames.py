'''This module defines the important coordinate systems to be used in
reconstruction with the CTA pipeline and the transformations between
this different systems. Frames and transformations are defined using
the astropy.coordinates framework. This module contains transformations
between angular systems.

For examples on usage see examples/coordinate_transformations.py

This code is based on the coordinate transformations performed in the
read_hess code

TODO:

- Tests Tests Tests!
- Check cartesian system is still accurate for the nominal and
  telescope systems (may need a spherical system)
- Benchmark transformation time
- should use `astropy.coordinates.Angle` for all angles here
'''

import astropy.units as u
import numpy as np
from astropy.coordinates import (
    BaseCoordinateFrame,
    CartesianRepresentation,
    UnitSphericalRepresentation,
    FunctionTransform,
    AltAz
)

try:
    # FrameAttribute was renamed Attribute in astropy 2.0
    # TODO: should really use subclasses like QuantityAttribute
    from astropy.coordinates import FrameAttribute as Attribute
except ImportError:
    from astropy.coordinates import Attribute

from astropy.coordinates import frame_transform_graph
from astropy.coordinates.matrix_utilities import rotation_matrix
from ..coordinates.representation import PlanarRepresentation

__all__ = [
    'CameraFrame',
    'TelescopeFrame',
]


class CameraFrame(BaseCoordinateFrame):
    '''
    Camera coordinate frame.

    The camera frame is a simple physical cartesian frame,
    describing the 2 dimensional position of objects
    in the focal plane of the telescope.

    Most typically this will be used to describe the positions
    of the pixels in the focal plane.

    Attributes
    ----------

    rotation: astropy.coordinates.Angle or astropy.units.Quantity
        Rotation angle of the camera (0 deg in most cases)
    '''
    default_representation = PlanarRepresentation
    rotation = Attribute(default=0 * u.deg)


class TelescopeFrame(BaseCoordinateFrame):
    '''
    Telescope coordinate frame.

    Spherical coordinate system to describe the
    angular offset of a given position in reference to pointing
    direction of a given telescope.

    Attributes
    ----------

    pointing_direction: astropy.coordinates.AltAz
        AltAz direction of the telescope pointing
    focal_length: astropy.units.Quantity
        Focal length of the telescope as an astropy quantity of length
    '''
    default_representation = UnitSphericalRepresentation
    pointing_direction = Attribute(default=None)
    focal_length = Attribute(default=None)

    @property
    def offset_angle_x(self):
        '''
        Offset angle to the optical axis along the x-axis of the
        cartesian representation
        '''
        cartesian = self.cartesian
        return np.arctan2(cartesian.x, cartesian.z)

    @property
    def offset_angle_y(self):
        '''
        Offset angle to the optical axis along the x-axis of the
        cartesian representation
        '''
        cartesian = self.cartesian
        return np.arctan2(cartesian.y, cartesian.z)




@frame_transform_graph.transform(FunctionTransform, TelescopeFrame, AltAz)
def telescope_to_altaz(telescope_frame, altaz):
    ''' Transform a coordinate from CameraFrame to AltAz '''

    if telescope_frame.pointing_direction is None:
        raise AttributeError('Pointing Direction must be set')

    cartesian = telescope_frame.cartesian.copy()

    rot_z_az = rotation_matrix(-telescope_frame.pointing_direction.az, 'z')
    rot_y_zd = rotation_matrix(-telescope_frame.pointing_direction.zen, 'y')

    cartesian = cartesian.transform(rot_y_zd)
    cartesian = cartesian.transform(rot_z_az)

    return AltAz(cartesian, location=altaz.location, obstime=altaz.obstime)


@frame_transform_graph.transform(FunctionTransform, AltAz, TelescopeFrame)
def altaz_to_telescope(altaz, telescope_frame):
    cartesian = altaz.cartesian

    rot_z_az = rotation_matrix(telescope_frame.pointing_direction.az, 'z')
    rot_y_zd = rotation_matrix(telescope_frame.pointing_direction.zen, 'y')

    cartesian = cartesian.transform(rot_z_az)
    cartesian = cartesian.transform(rot_y_zd)

    return TelescopeFrame(
        representation=cartesian,
        focal_length=telescope_frame.focal_length,
    )


@frame_transform_graph.transform(FunctionTransform, TelescopeFrame, CameraFrame)
def telescope_to_camera(telescope_frame, camera_frame):
    '''
    Transformation between TelescopeFrame and CameraFrame

    Parameters
    ----------
    telescope_frame: ctapipe.coordinates.TelescopeFrame
        TelescopeFrame system
    camera_frame: ctapipe.coordinates.CameraFrame
        CameraFrame system

    Returns
    -------
    coordinates: ctapipe.coordinates.CameraFrame
    '''
    focal_length = telescope_frame.focal_length

    cartesian = telescope_frame.cartesian.copy()
    rot_camera = rotation_matrix(camera_frame.rotation, 'z')
    rotated = cartesian.transform(rot_camera)

    # This is not a typo. The x-axis of the telescope-frame's
    # cartesian representation is oriented along the zenith-axis
    # which should be along the y axis in the camera frame.
    y = focal_length * rotated.x / rotated.z
    x = -focal_length * rotated.y / rotated.z

    return CameraFrame(x=x, y=y)


@frame_transform_graph.transform(FunctionTransform, CameraFrame, TelescopeFrame)
def camera_to_telescope(camera_frame, telescope_frame):
    '''
    Transformation between TelescopeFrame and CameraFrame

    Parameters
    ----------
    telescope_frame: ctapipe.coordinates.TelescopeFrame
        TelescopeFrame system
    camera_frame: ctapipe.coordinates.CameraFrame
        CameraFrame system

    Returns
    -------
    coordinates: ctapipe.coordinates.CameraFrame
    '''
    focal_length = telescope_frame.focal_length

    # This is not a typo. The x-axis of the telescope-frame's
    # cartesian representation is oriented along the zenith-axis
    # which should be along the y axis in the camera frame.
    u = camera_frame.x
    v = camera_frame.y

    z = 1 / np.sqrt(1 + (u / focal_length)**2 + (v / focal_length)**2)

    cartesian = CartesianRepresentation(
        x=z * v / focal_length,
        y=- z * u / focal_length,
        z=z
    )

    rot_camera = rotation_matrix(-camera_frame.rotation, 'z')
    rotated = cartesian.transform(rot_camera)

    return TelescopeFrame(
        rotated,
        focal_length=focal_length,
        pointing_direction=telescope_frame.pointing_direction,
    )
