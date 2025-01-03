import cpu.iss.riscv
import memory.memory
import vp.clock_domain
import interco.router
import utils.loader.loader
import gvsoc.systree
import gvsoc.runner
import my_comp


GAPY_TARGET = True

class Soc(gvsoc.systree.Component):

    def __init__(self, parent, name, parser):
        super().__init__(parent, name)

        # Parse the arguments to get the path to the binary to be loaded
        [args, __] = parser.parse_known_args()

        binary = args.binary

        # Main interconnect
        ico = interco.router.Router(self, 'ico')

        # Custom components
        comp = my_comp.MyComp(self, 'my_comp', value=0x12345678)
        ico.o_MAP(comp.i_INPUT(), 'comp', base=0x20000000, size=0x00001000, rm_base=True)

        comp2 = my_comp.MyComp2(self, 'my_comp2')
        ico.o_MAP(comp2.i_INPUT(), 'comp2', base=0x30000000, size=0x00001000, rm_base=True)
        comp2.o_POWER_CTRL( comp.i_POWER  ())
        comp2.o_VOLTAGE_CTRL( comp.i_VOLTAGE())

        # Main memory
        mem = memory.memory.Memory(self, 'mem', size=0x00100000)
        # The memory needs to be connected with a mpping. The rm_base is used to substract
        # the global address to the requests address so that the memory only gets a local offset.
        ico.o_MAP(mem.i_INPUT(), 'mem', base=0x00000000, size=0x00100000, rm_base=True)

        mem.add_properties({
            "background": {
                "dynamic": {
                    "type": "linear",
                    "unit": "W",

                    "values": {
                        "25": {
                            "1.2": {
                                "any": "0.0001"
                            }
                        }
                    }
                },
                "leakage": {
                    "type": "linear",
                    "unit": "W",

                    "values": {
                        "25": {
                            "1.2": {
                                "any": "0.000001"
                            }
                        }
                    }
                }
            },
            "read_32": {
                "dynamic": {
                    "type": "linear",
                    "unit": "pJ",

                    "values": {
                        "25": {
                            "1.2": {
                                "any": "1.5"
                            }
                        }
                    }
                }
            },
            "write_32": {
                "dynamic": {
                    "type": "linear",
                    "unit": "pJ",

                    "values": {
                        "25": {
                            "1.2": {
                                "any": "2.5"
                            }
                        }
                    }
                }
            }
        })



        # Instantiates the main core and connect fetch and data to the interconnect
        host = cpu.iss.riscv.Riscv(self, 'host', isa='rv64imafdc')
        host.o_FETCH     ( ico.i_INPUT     ())
        host.o_DATA      ( ico.i_INPUT     ())

        # Finally connect an ELF loader, which will execute first and will then
        # send to the core the boot address and notify him he can start
        loader = utils.loader.loader.ElfLoader(self, 'loader', binary=binary)
        loader.o_OUT     ( ico.i_INPUT     ())
        loader.o_START   ( host.i_FETCHEN  ())
        loader.o_ENTRY   ( host.i_ENTRY    ())

        mem2 = memory.memory.Memory(self, 'mem2', size=0x00100000, power_trigger=True)
        ico.o_MAP(mem2.i_INPUT(), 'mem2', base=0x10000000, size=0x00100000, rm_base=True)


# This is a wrapping component of the real one in order to connect a clock generator to it
# so that it automatically propagate to other components
class Rv64(gvsoc.systree.Component):

    def __init__(self, parent, name, parser, options):

        super().__init__(parent, name, options=options)

        clock = vp.clock_domain.Clock_domain(self, 'clock', frequency=100000000)
        soc = Soc(self, 'soc', parser)
        clock.o_CLOCK    ( soc.i_CLOCK     ())




# This is the top target that gapy will instantiate
class Target(gvsoc.runner.Target):

    def __init__(self, parser, options):
        super(Target, self).__init__(parser, options,
            model=Rv64, description="RV64 virtual board")
