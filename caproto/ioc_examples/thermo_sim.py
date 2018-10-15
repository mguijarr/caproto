#!/usr/bin/env python3
import argparse
from caproto.server import pvproperty, PVGroup, template_arg_parser, run
import numpy as np
import time
from textwrap import dedent



class Thermo(PVGroup):
    """
    Simulates (poorly) an oscillating temperature controller.

    Follows :math:`T_{output} = T_{var} exp^{-(t - t_0)/K} sin(ω t) + T_{setpoint}`

    The default prefix is `thermo:`

    Readonly PVs
    ------------

    I -> the current value

    Control PVs
    -----------

    SP -> where to go
    K -> the decay constant
    omega -> the oscillation frequency
    Tvar -> the scale of the oscillations
    """

    def __init__(self, *args, period, **kwargs):
        super().__init__(*args, **kwargs)
        self._T0 = time.monotonic()
        self.period = period

    readback = pvproperty(value=0, dtype=float, read_only=True,
                          name='I',
                          mock_record='ai')

    setpoint = pvproperty(value=100, dtype=float, name='SP')
    K = pvproperty(value=10, dtype=float)
    omega = pvproperty(value=np.pi, dtype=float)
    Tvar = pvproperty(value=10, dtype=float)

    @readback.scan(period=.1, use_scan_field=True)
    async def readback(self, instance, async_lib):

        def t_rbv(T0, setpoint, K, omega, Tvar,):
            t = time.monotonic()
            return ((Tvar *
                     np.exp(-(t - self._T0) / K) *
                     np.sin(omega * t)) +
                    setpoint)

        T = t_rbv(T0=self._T0,
                  **{k: getattr(self, k).value
                     for k in ['setpoint', 'K', 'omega', 'Tvar']})

        await instance.write(value=T)

    @setpoint.putter
    async def setpoint(self, instance, value):
        self._T0 = time.monotonic()
        return value


if __name__ == '__main__':
    parser, split_args = template_arg_parser(
        default_prefix='thermo:',
        desc=dedent(Thermo.__doc__))

    def in_range(v):
        v = float(v)
        if not (0 < v < 1):
            raise argparse.ArguementTypeError(f" {v} not in range [0, 1]")
        return v

    parser.add_argument('--period',
                        help='The update rate of the readback',
                        type=float,
                        default=0.1)

    args = parser.parse_args()
    ioc_options, run_options = split_args(args)
    ioc = Thermo(period=args.period, **ioc_options)
    run(ioc.pvdb, **run_options)
