"""Basic tests for the Python base container images."""
import pytest
import time
from bci_tester.data import PYTHON310_CONTAINER
from bci_tester.data import PYTHON36_CONTAINER
from bci_tester.data import PYTHON39_CONTAINER
from pytest_container import DerivedContainer
from pytest_container.container import container_from_pytest_param
from pytest_container.runtime import LOCALHOST

bcdir = "/tmp/"
orig = "tests/"
appdir = "trainers/"
outdir = "output/"
appl1 = "tensorflow_examples.py"
t0 = time.time()

# copy tensorflow module trainer from the local application directory to the container
DOCKERF_PY_T = f"""
WORKDIR {bcdir}
RUN mkdir {appdir}
RUN mkdir {outdir}
COPY {orig + appdir}/{appl1}  {appdir}
"""

# Base containers under test, input of auto_container fixture
CONTAINER_IMAGES = [
    PYTHON36_CONTAINER,
    PYTHON39_CONTAINER,
    PYTHON310_CONTAINER,
]

# Derived containers including additional test files, parametrized per test
CONTAINER_IMAGES_T = [
    pytest.param(
        DerivedContainer(
            base=container_from_pytest_param(CONTAINER_T),
            containerfile=DOCKERF_PY_T,
        ),
        marks=CONTAINER_T.marks,
        id=CONTAINER_T.id,
    )
    for CONTAINER_T in CONTAINER_IMAGES
]


@pytest.mark.parametrize(
    "container_per_test", CONTAINER_IMAGES_T, indirect=["container_per_test"]
)
@pytest.mark.parametrize("hmodule, port, timeout", [("http.server", 8123, 30)])
def test_python_webserver_1(container_per_test, hmodule, port, timeout):
    """Test that the python webserver is able to open a given port"""

    portstatus = False

    processlist = None

    # pkg neeed to run socket/port check
    if not container_per_test.connection.package("iproute2").is_installed:
        container_per_test.connection.run_expect([0], "zypper -n in iproute2")

    # checks that the expected port is Not listening yet
    assert not container_per_test.connection.socket(
        f"tcp://0.0.0.0: {port}"
    ).is_listening
    
    print(1,time.time()-t0)

    # start of the python http server
    container_per_test.connection.run_expect(
        [0], f"timeout --preserve-status 100 python3 -m {hmodule} {port} &"
    )

    print(2,time.time()-t0)

    # race conditions prevention: port status inspection with timeout
    for t in range(timeout):
        time.sleep(1)
        portstatus = container_per_test.connection.socket(
            f"tcp://0.0.0.0: {port}"
        ).is_listening
        print(3.0,time.time()-t0)
        if portstatus:
            break

    print(4,time.time()-t0)

    # check inspection success or timeeout
    assert portstatus, "timeout expired: expected port not listening"

    # collect running processes (see man ps BSD options)
    processlist = container_per_test.connection.run_expect(
        [0], "ps axho command"
    )

    # check also that server is running
    assert hmodule in processlist.stdout, f"{hmodule} not running."

