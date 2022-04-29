"""Basic tests for the Python 3.6 and 3.9 base container images."""
from bci_tester.data import PYTHON310_CONTAINER
from bci_tester.data import PYTHON36_CONTAINER
from bci_tester.data import PYTHON39_CONTAINER

import pytest
from _pytest.mark.structures import ParameterSet
from pytest_container import DerivedContainer
from pytest_container.container import container_from_pytest_param

wrk = "/tmp/"
src = "tests/"
rep = "trainers/"
out = "output/"
fil = "README.md"

DOCKERF_PY_T = f"""
WORKDIR {wrk}
RUN mkdir {rep}
RUN mkdir {out}
COPY {src + rep}  {rep}
"""

PYTHON36_CONTAINER_T = pytest.param(
    DerivedContainer(
        base=container_from_pytest_param(PYTHON36_CONTAINER),
        containerfile=DOCKERF_PY_T,
    ),
    marks=PYTHON36_CONTAINER.marks,
)

PYTHON39_CONTAINER_T = pytest.param(
    DerivedContainer(
        base=container_from_pytest_param(PYTHON39_CONTAINER),
        containerfile=DOCKERF_PY_T,
    ),
    marks=PYTHON39_CONTAINER.marks,
)

PYTHON310_CONTAINER_T = pytest.param(
    DerivedContainer(
        base=container_from_pytest_param(PYTHON310_CONTAINER),
        containerfile=DOCKERF_PY_T,
    ),
    marks=PYTHON310_CONTAINER.marks,
)

CONTAINER_IMAGES = [
    PYTHON36_CONTAINER_T,
    PYTHON39_CONTAINER_T,
    PYTHON310_CONTAINER_T,
]


def test_python_version(auto_container):
    """Test that the python version equals the value from the environment variable
    ``PYTHON_VERSION``.

    """
    reported_version = auto_container.connection.run_expect(
        [0], "python3 --version"
    ).stdout.strip()
    version_from_env = auto_container.connection.run_expect(
        [0], "echo $PYTHON_VERSION"
    ).stdout.strip()

    assert reported_version == f"Python {version_from_env}"


def test_pip(auto_container):
    """Check that :command:`pip` is installed and its version equals the value from
    the environment variable ``PIP_VERSION``.

    """
    assert auto_container.connection.pip.check().rc == 0
    reported_version = auto_container.connection.run_expect(
        [0], "pip --version"
    ).stdout
    version_from_env = auto_container.connection.run_expect(
        [0], "echo $PIP_VERSION"
    ).stdout.strip()

    assert f"pip {version_from_env}" in reported_version


def test_tox(auto_container):
    """Ensure we can use :command:`pip` to install :command:`tox`."""
    auto_container.connection.run_expect([0], "pip install --user tox")


def test_python_webserver_1(auto_container_per_test, host, container_runtime):
    """Test that the simple python webserver answers to an internal get request"""

    import time

    # ID of the running container under test
    c_id = auto_container_per_test.container_id

    xfilename = "file_to_get1.txt"

    port = "8001"

    # expected result
    okget = "200 OK"

    _serv = "nohup timeout 240s python3 -m http.server " + port + " &"

    _wget = (
        "timeout 240s wget -d -S -w 4 -t 4 http://localhost:"
        + port
        + "/"
        + xfilename
        + " 2>&1 | tee log.txt"
    )

    _curl = (
        "timeout 240s curl http://localhost:"
        + port
        + "/"
        + xfilename
        + " 2>&1 | tee log.txt"
    )

    x = None

    # check needed commands present
    if not auto_container_per_test.connection.package("curl").is_installed:
        auto_container_per_test.connection.run_expect([0], "zypper -n in curl")

    if not auto_container_per_test.connection.package("wget").is_installed:
        auto_container_per_test.connection.run_expect([0], "zypper -n in wget")

    if not auto_container_per_test.connection.package("iproute2").is_installed:
        auto_container_per_test.connection.run_expect(
            [0], "zypper -n in iproute2"
        )

    # copy a local file in the running Container under test
    host.run_expect(
        [0],
        f"{container_runtime.runner_binary} cp {src + rep + fil} {c_id}:{wrk + xfilename}",
    )

    # check that the expected file to be fetched from the server is present in the container
    assert auto_container_per_test.connection.file(wrk + xfilename).exists

    # start of the python http server
    auto_container_per_test.connection.run_expect([0], _serv)

    # check of expected port is listening
    assert auto_container_per_test.connection.socket(
        "tcp://0.0.0.0:" + port
    ).is_listening

    # check for python http.server process running in container
    proc = auto_container_per_test.connection.process.filter(comm="python3")

    for p in proc:
        x = p.args
        if "http.server" in x:
            break

    # check keywork present
    assert "http.server" in x, "http.server not running."

    # get file from server using wget
    for x in range(4):
        time.sleep(10)
        if (
            auto_container_per_test.connection.run_expect(
                [0],
                _wget,
            ).exit_status
            == 0
        ):
            break

    ## check expected result for wget
    auto_container_per_test.connection.run_expect(
        [0], 'grep "' + okget + '" log.txt'
    )

    # get file from server using curl
    for x in range(4):
        time.sleep(10)
        if (
            auto_container_per_test.connection.run_expect(
                [0],
                _curl,
            ).exit_status
            == 0
        ):
            break

    # check expected result for curl:
    # expected that No[1] error present in log
    assert auto_container_per_test.connection.run_expect(
        [1], 'grep -E "Error |Empty " log.txt'
    )


def test_python_webserver_2(auto_container_per_test, host, container_runtime):
    """Test that the simple python webserver answers to an internal get request"""

    # ID of the running container under test
    c_id = auto_container_per_test.container_id

    outdir = wrk + out

    mpy = rep + "communication_examples.py"

    xfilename = "file_to_get2.txt"

    port = "8002"

    _serv = "nohup timeout 240s python3 -m http.server " + port + " &"

    _wget = (
        "timeout 240s python3 "
        + mpy
        + " http://127.0.0.1:"
        + port
        + "/"
        + xfilename
        + " "
        + outdir
    )

    _wgetko = (
        "python3 " + mpy + " http://127.0.0.1:9999/" + xfilename + " " + outdir
    )

    # check the test python module is present in the container
    assert auto_container_per_test.connection.file(wrk + mpy).is_file

    # install wget for python
    auto_container_per_test.connection.run_expect([0], "pip install wget")

    # check needed commands present
    if not auto_container_per_test.connection.package("iproute2").is_installed:
        auto_container_per_test.connection.run_expect(
            [0], "zypper -n in iproute2"
        )

    # copy a local file in the running Container under test
    host.run_expect(
        [0],
        f"{container_runtime.runner_binary} cp {src + rep + fil} {c_id}:{wrk + xfilename}",
    )

    # check for expected file present in source
    assert auto_container_per_test.connection.file(xfilename).exists

    # start of the python http server in the workdir
    auto_container_per_test.connection.run_expect([0], _serv)

    # check of expected port is listening
    assert auto_container_per_test.connection.socket(
        "tcp://0.0.0.0:" + port
    ).is_listening

    # check for python http.server process is running in the container
    proc = auto_container_per_test.connection.process.filter(comm="python3")

    # find the server
    for p in proc:
        a = p.args
        if "http.server" in a:
            break

    assert "http.server" in a, "http.server not running."

    # check expected file NOT present yet in destination dir.
    assert not auto_container_per_test.connection.file(
        outdir + xfilename
    ).exists

    # run the test in the container: expected FAIL for wrong port
    assert auto_container_per_test.connection.run_expect([1], _wgetko)

    # run the test in the container and check expected keyword from the module
    assert (
        "PASS"
        in auto_container_per_test.connection.run_expect([0], _wget).stdout
    )

    # check expected file present in the destination
    assert auto_container_per_test.connection.file(outdir + xfilename).exists


def test_tensorf(auto_container_per_test):
    """Test that a tensorflow example works."""

    mpy = "tensorflow_examples.py"

    # commands for tests using python modules in the container, copied from local
    _vers = 'python3 -c "import tensorflow as tf; print (tf.__version__)" 2>&1|tail -1;'

    _test = "timeout 240s python3 " + rep + mpy

    # check the test python module is present in the container
    assert auto_container_per_test.connection.file(wrk + rep + mpy).is_file

    # check the expected CPU flag for TF is available in the system
    flg = auto_container_per_test.connection.run_expect(
        [0], "lscpu| grep -c -i SSE4.. "
    ).stdout

    assert int(flg) > 0

    # install TF module for python
    auto_container_per_test.connection.run_expect(
        [0], "pip install tensorflow"
    )

    ver = auto_container_per_test.connection.run_expect(
        [0], _vers
    ).stdout.strip()

    # TF version: for python 3.x - tf > 2.0
    assert int(ver[0]) >= 2

    # Exercise execution
    xout = auto_container_per_test.connection.run_expect([0], _test)

    # keyword search
    assert "accuracy" in xout.stdout

    # expected keyword value found: PASS
    assert "PASS" in xout.stdout
