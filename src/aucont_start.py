import os
import subprocess
import sys
import ipaddress
import uuid


def setup_net(ip, cont_pid):
    host_ip = str(int(ipaddress.ip_address(ip)) + 1)
    host_veth_name = "veth" + str(cont_pid)
    cont_veth_name = "veth1"

    subprocess.call(["ip", "link", "add", host_veth_name, "type", "veth", "peer", "name", cont_veth_name])
    subprocess.call(["ip", "link", "set", cont_veth_name, "netns", cont_pid])
    subprocess.call(["ip", "netns", "exec", cont_pid, "ip", "link", "set", cont_veth_name, "up"])
    subprocess.call(["ip", "netns", "exec", cont_pid, "ip", "addr", "add", ip + "/24", "dev", cont_veth_name])
    subprocess.call(["ip", "link", "set", host_veth_name, "up", "&&",
                     "ip", "addr", "add", host_ip + "/24", "dev", host_veth_name])


def setup_cpu(perc, cont_pid):
    cgroup_path = "/sys/fs/cgroup/cpu/" + str(cont_pid)
    period = 1000000
    quota = int(perc) * period / 100

    subprocess.call(["mkdir", cgroup_path])
    subprocess.call(["echo", str(cont_pid), ">", cgroup_path + "/tasks"])
    subprocess.call(["echo", period, ">", cgroup_path + "cpu.cfs_period_us"])
    subprocess.call(["echo", quota, ">", cgroup_path + "cpu.cfs_quota_us"])


def setup_workplace(img_path):
    pass


def main(argv):
    print(argv[0], file=sys.stderr)

    c_cmd = ["./aucont_start.elf"]
    net_idx = -1
    cpu_idx = -1

    i = 1
    while argv[i][0] == "-":
        if argv[i] == "-d":
            c_cmd.append("1")
            i += 1
        elif argv[i] == "--net":
            net_idx = i + 1
            i += 2
        elif argv[i] == "--cpu":
            cpu_idx = i + 1
            i += 2
    if len(c_cmd) == 1:
        c_cmd.append("0")
    img_path = argv[i]

    # setup workplace
    archive_path = "/test/images/"
    unique_name = str(uuid.uuid4())
    dest_path = "/test/containers/" + unique_name + "/"
    c_cmd.append(dest_path)
    c_cmd.extend(argv[i + 1:])

    os.makedirs(archive_path, exist_ok=True)
    os.makedirs(dest_path, exist_ok=False)
    subprocess.call("(cd {0}; tar cf - .) | (cd {1}; tar xf -)".format(img_path, dest_path))

    # create namespaces, obtain PID
    output = subprocess.check_output(c_cmd, stderr=subprocess.STDOUT)
    cont_pid = output.decode('UTF-8')[:-1]
    str_pid = str(cont_pid)

    id_file = open(archive_path + str_pid, 'w')
    id_file.write(unique_name)
    id_file.close()
    pid_file = open(dest_path + "PID", 'w')
    pid_file.write(cont_pid)
    pid_file.close()

    # setup network and/or resources if needed
    if net_idx != -1:
        setup_net(argv[net_idx], cont_pid)
    if cpu_idx != -1:
        setup_cpu(argv[cpu_idx], cont_pid)

    print(cont_pid, sys.stdout)