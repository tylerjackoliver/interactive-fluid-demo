from numba import jit
import numpy as np
import cv2

from DensityField import DensityField
import util.colour_util as colour_util

# Base class for the fluid sims. Handles the update and render calls, as well as
# encapsulating a bunch of arrays
class SimBase:
    def __init__(self, cam_shape, res_multiplier):
        self._cam_shape = cam_shape
        self._shape = (int(cam_shape[0] * res_multiplier), int(cam_shape[1] * res_multiplier))
        self._mode = 0
        self._v = np.zeros((2, *self._shape)) # velocity field
        self._b = np.zeros(self._shape, dtype=bool) # boundary
        self._notb = np.logical_not(self._b) # inverse boundary
        self._dx = np.array([4/3,1]) / np.array(self._shape) # discretisation

        self._d = DensityField(self._shape) # density fields
        self._flowwidth = 0
        self._flowdirection = 0

        # HSV velocity render
        self._hsv_field = np.zeros((3, *self._shape), dtype=np.uint8)
        self._hsv_field[1] = 255

        # temp arrays used when rendering
        self._float3tmp = np.zeros((3, *cam_shape)[::-1], dtype=float)
        self._float1tmp = np.zeros(cam_shape[::-1], dtype=float)
        self._simshapetmp = np.zeros((3, *self._shape)[::-1], dtype=np.uint8)
        self._camshapetmp = np.zeros((3, *cam_shape)[::-1], dtype=np.uint8)
        self._output = np.zeros((3, *cam_shape)[::-1], dtype=np.uint8)

    @property
    def shape(self):
        return self._shape

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        self._mode = value

    @jit
    def set_boundary(self, cell_ocupation, boundary_velocity, flow_direction):
        # input boundary
        self._b[:] = cell_ocupation
        self._v[:, self._b] = boundary_velocity[:, self._b]

        # add boundary walls parrallel to flow
        if flow_direction == 0:
            self._b[:, :1] = True
            self._b[:, -1:] = True
            self._v[:, :, :1] = 0
            self._v[:, :, -1:] = 0
        elif flow_direction == 1:
            self._b[:1, :] = True
            self._b[-1:, :] = True
            self._v[:, :1, :] = 0
            self._v[:, -1:, :] = 0
        elif flow_direction == 2:
            self._b[:, :1] = True
            self._b[:, -1:] = True
            self._v[:, :, :1] = 0
            self._v[:, :, -1:] = 0
        elif flow_direction == 3:
            self._b[:1, :] = True
            self._b[-1:, :] = True
            self._v[:, :1, :] = 0
            self._v[:, -1:, :] = 0

        # cache boundary inverse
        self._notb = np.logical_not(self._b)

    @jit
    def set_velocity(self, dt, flow_speed, flow_direction, num_streams, smoke_amount):
        # As flow velocity increase, increase with of area to which it is applied.
        # This means advection pulls from inside the flow.
        flowwidth = 1 + int(dt * flow_speed / self._dx[0])

        # Apply flow velocity to boundary layer perpendicular to flow
        if flow_direction == 0:
            self._v[0, :flowwidth, :] = flow_speed
            self._v[0, -flowwidth:, :] = flow_speed
            self._v[1, :flowwidth, :] = 0
            self._v[1, -flowwidth:, :] = 0
        elif flow_direction == 1:
            self._v[0, :, :flowwidth] = 0
            self._v[0, :, -flowwidth:] = 0
            self._v[1, :, :flowwidth] = flow_speed
            self._v[1, :, -flowwidth:] = flow_speed
        elif flow_direction == 2:
            self._v[0, :flowwidth, :] = -flow_speed
            self._v[0, -flowwidth:, :] = -flow_speed
            self._v[1, :flowwidth, :] = 0
            self._v[1, -flowwidth:, :] = 0
        elif flow_direction == 3:
            self._v[0, :, :flowwidth] = 0
            self._v[0, :, -flowwidth:] = 0
            self._v[1, :, :flowwidth] = -flow_speed
            self._v[1, :, -flowwidth:] = -flow_speed

        # if not debug mode, update the denisty fields
        if self._mode == 0:
            self._d.add_density(flowwidth, flow_direction, num_streams, smoke_amount)

    @jit
    def get_velocity(self):
        return self._v

    @jit
    def reset(self):
        self._v[:] = 0
        self._d.reset()

    @jit
    def get_velocity_field_as_HSV(self, power=0.5):
        # map velocity per grid point to hue (direction) and value (magnitude)
        self._hsv_field[0] = 180 * (np.arctan2(-self._v[0], -self._v[1]) / (2 * np.pi) + 0.5)
        # self._hsv_field[1] = 255
        self._hsv_field[2] = 255 * (self._v[0]**2 + self._v[1]**2) ** power
        return self._hsv_field

    @jit
    def udpate(self, dt):
        # update and render the sim
        if self._mode == 0:
            self.step(dt, self._d.field)
        else:
            self.step(dt, [])

    @jit
    def render(self, camera, render_mask_velocity=False, render_mask=False):
        # update and render the sim
        if self._mode == 0:
            # combine the density fields with the input camera frame
            cv2.resize(self._d.get_render().T, camera.shape, dst=self._float3tmp)
            cv2.resize(self._d.get_alpha().T, camera.shape, dst=self._float1tmp)
            self._output[:] = 255 * (self._float3tmp * self._float1tmp[:,:,np.newaxis]) \
                + camera.input_frame * (1 - self._float1tmp[:,:,np.newaxis])
            if render_mask:
                # optionally render a copy of the mask
                self._output[:camera.shape[1]//4,:camera.shape[0]//4] = \
                    cv2.resize(camera.mask, (camera.shape[0]//4, camera.shape[1]//4))[:,:,np.newaxis]
        else:

            # render the velocity field
            cv2.cvtColor(self.get_velocity_field_as_HSV(0.25).T, cv2.COLOR_HSV2BGR, dst=self._simshapetmp) # should be 0.5 (i.e. square root), but this shows the lower velocities better
            cv2.resize(self._simshapetmp, camera.shape, dst=self._output)

            if render_mask:
                # render the pressure solution as range from blue (negative) to red (positive)
                # self._simshapetmp[:] = self.get_pressure_as_rgb().T * 512
                # cv2.resize(self._simshapetmp, camera.shape, dst=self._camshapetmp)
                # cv2.blur(self._camshapetmp, (20, 20), dst=self._camshapetmp)
                self._camshapetmp[:] = 0
                # add the the cam mask
                cv2.add(cv2.cvtColor(camera.mask // 4, cv2.COLOR_GRAY2BGR), self._camshapetmp, dst=self._camshapetmp)

                # combine using the mask to select between the two renders
                cv2.add(self._output, self._camshapetmp, dst=self._output, mask=camera.mask)

        return self._output
