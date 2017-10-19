from astropy.coordinates import AltAz
import astropy.units as u


def test_altaz_to_camera():
    from ctapipe.coordinates import CameraFrame, TelescopeFrame

    pointing_direction = AltAz(alt=80 * u.deg, az=0 * u.deg)
    source_position = AltAz(alt=79.4 * u.deg, az=0 * u.deg)
    focal_length = 4889 * u.mm

    fact_camera_frame = CameraFrame(
        # rotation=90 * u.deg,
    )


    fact_telescope_frame = TelescopeFrame(
        pointing_direction=pointing_direction,
        focal_length=focal_length,
    )

    telescope_coord = source_position.transform_to(fact_telescope_frame)
    camera_coord = telescope_coord.transform_to(fact_camera_frame)

    print(camera_coord)




def test_camera_to_altaz():
    from ctapipe.coordinates import CameraFrame, TelescopeFrame

    pointing_direction = AltAz(alt=80 * u.deg, az=0 * u.deg)
    focal_length = 4889 * u.mm

    camera = CameraFrame(
        9.5 * u.mm, 0 * u.mm,
        rotation=90 * u.deg,
    )

    fact_telescope_frame = TelescopeFrame(
        pointing_direction=pointing_direction,
        focal_length=focal_length,
    )

    telescope_coord = camera.transform_to(fact_telescope_frame)
    alt_az_coord = telescope_coord.transform_to(AltAz)

    print(alt_az_coord)



if __name__ == '__main__':
    test_altaz_to_camera()
    test_camera_to_altaz()
