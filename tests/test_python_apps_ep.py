"""Basic tests for the Python base container images."""
import pytest
import time
from bci_tester.data import PYTHON310_CONTAINER
from bci_tester.data import PYTHON36_CONTAINER
from bci_tester.data import PYTHON39_CONTAINER
from pytest_container import DerivedContainer
from pytest_container.container import container_from_pytest_param
from pytest_container.runtime import LOCALHOST

a1=time.time()

bcdir = "/tmp/"

# copy tensorflow module trainer from the local application directory to the container
DOCKERF_PY_T = f"""
WORKDIR {bcdir}
RUN echo "while true; do sleep 5; printf TIME=; date; done" > prov.sh
RUN chmod 777 prov.sh
EXPOSE 8123
"""

DOCKERF_PY_T2 = f"""
WORKDIR {bcdir}
EXPOSE 8123
RUN echo "Hallo! http server running ok PASS" > index.html
ENTRYPOINT ["python3", "-m", "http.server", "8123", "&"]
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


# Derived containers including additional test files, parametrized per test
CONTAINER_IMAGES_T2 = [
    pytest.param(
        DerivedContainer(
            base=container_from_pytest_param(CONTAINER_T),
            containerfile=DOCKERF_PY_T2,
            extra_launch_args=["-p", "8080:8123"],
        ),
        marks=CONTAINER_T.marks,
        id=CONTAINER_T.id,
    )
    for CONTAINER_T in CONTAINER_IMAGES
]





@pytest.mark.parametrize(
    "container", CONTAINER_IMAGES_T2, indirect=["container"]
)
def test_python_webserver_3(container, host):
    """Test that the python webserver is able to open a given port"""

    port = "8123"
    hmodule = "http.server"
    
    ptimeout = 10

    portstatus = False
    processlist = None
    proc=None
    proc1=None
    runx = True
    runy = True 
    runf = True
    cb=None
    cd=None
    ca=None
    t = None

    
    print(1,time.time()-a1)

    cb = host.run("curl 0.0.0.0:8123")
    cd = host.run("curl localhost:8080")
    ca = host.run("curl localhost:8123")
    cc = host.run("curl 0.0.0.0:8080")

    print(12,time.time()-a1,cb.stdout)    
    print(13,time.time()-a1,cd.stdout)
    print(14,time.time()-a1,ca.stdout)
    print(14,time.time()-a1,cc.stdout)

    cb = host.run("lsof -i:8123")
    cd = host.run("lsof -i:8080")
    ca = host.run("wget http://0.0.0.0:8123")


    print(15,time.time()-a1,cb.stdout)    
    print(16,time.time()-a1,cd.stdout)
    print(17,time.time()-a1,ca.stdout)

    ca = host.run("ss --listen --numeric --tcp")
    
    print(18,time.time()-a1,ca.stdout)
    
    
    # pkg neeed to process check
    #if not container.connection.package("iproute2").is_installed:
    #    container.connection.run_expect([0], "zypper -n in iproute2")

    # pkg neeed to process check
    #if not container.connection.package("wget").is_installed:
    #    container.connection.run_expect([0], "zypper -n in wget")

    #print(2,time.time()-a1)
    

    # checks that the expected port is Not listening yet
    #assert not container.connection.socket(
    #    "tcp://0.0.0.0:" + port
    #).is_listening


    print(3,time.time()-a1)

    # start of the python http server
    bci_pyt_serv = container.connection.run(
        # f"timeout --preserve-status 200s python3 -m http.server {port} &",
        f"ps -ax"
    )

    proc1=bci_pyt_serv

    print(31,time.time()-a1)
    
    #proc = container.connection.process.filter(comm="python3")
    
    #print(32,time.time()-a1)

    print(32,time.time()-a1, bci_pyt_serv.rc , bci_pyt_serv.stdout ,bci_pyt_serv.stderr )
     
    # start of the python http server
    #bci_pyt_serv = container.connection.run_expect(
    #    [0], f"timeout 200s python3 -m http.server {port} &"
    #).stdout


    
    #print(4,time.time()-a1)

    # race conditions prevention: port status inspection with timeout
    for t in range(ptimeout):
 

        print("5start",time.time()-a1)
        cb = host.run("curl localhost:8123").stdout
        cd = host.run("curl localhost:8080").stdout
        ca = host.run("curl localhost:8000").stdout
        print(50,time.time()-a1,ca,cb,cd)
        # if False:
        #proc1 = container.connection.run_expect(
        #        [0], "date; ls -la; date; ps -ax;date"
        #)

        #print(51,time.time()-a1, proc1.stdout, proc1.stderr)

        if runy:
            portstatus = container.connection.socket(
                f"tcp://0.0.0.0:{port}"
            ) .is_listening
            if portstatus:
                runy = False

        print(52,time.time()-a1, portstatus)

        if runx:
            processlist = container.connection.run_expect(
                [0], "ps axho command"
            )
            if hmodule in processlist.stdout:
                runx = False

        print(61,time.time()-a1, processlist)

        if runf:
            proc = container.connection.process.filter(comm="python3")
            if proc:
                runf = False
        
        print(62,time.time()-a1,proc)

        if not runx and not runy:
            break

        print(63,time.time()-a1)

        cb = host.run("lsof -i:8123").stdout
        #if port in cb:
        #    break

        print(613,time.time()-a1,cb)

        # cd = host.run("netstat -tulpn |grep 8123").stdout
        #if port in cd:
        #    break

        #print(62,time.time()-a1,cd)

        ca = host.run("wget localhost:8123").stdout
        #if port in ca:
        #    break
        
        print(614,time.time()-a1,ca)


        print(6000,time.time()-a1, t, portstatus, processlist, cb, cd,ca, proc)
        time.sleep(1)

    # check inspection success or timeeout
    # assert portstatus, "timeout expired: expected port not listening"
    print(7,time.time()-a1, t, portstatus, processlist, cb, cd,ca,proc)
    
  # collect running processes (see man ps BSD options)
    #processlist = container.connection.run_expect(
    #    [0], "ps axho command"
    #)
    print(8,time.time()-a1,bci_pyt_serv.rc, bci_pyt_serv.stdout,  bci_pyt_serv.stderr)
    
    assert portstatus, "port not open"
    # check also that server is running
    print(9,time.time()-a1)
    
    assert hmodule in processlist.stdout, f"{hmodule} not running."
    print(10,time.time()-a1)

    # checks that the python http.server process is running in the container:
    #proc = container.connection.process.filter(comm="python3")
    #print(proc)
    # check that the filtered list is not empty
    #assert 0 > 0, "The python3 http.server process must be running"


