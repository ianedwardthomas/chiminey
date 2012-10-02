from time import sleep

import paramiko
import os
import sys
import traceback
import logging

logger = logging.getLogger(__name__)

def is_ssh_ready(settings, ip_address):
    ssh_ready = False
    while not ssh_ready:
        try:
            ssh = open_connection(ip_address, settings)
            ssh_ready = True
        except Exception, e:
            sleep(settings['CLOUD_SLEEP_INTERVAL'])
            #print ("Connecting to %s in progress ..." % ip_address)
            #traceback.print_exc(file=sys.stdout)
    return ssh_ready

    
def open_connection(ip_address, settings):
    # open up the connection
    ssh = paramiko.SSHClient()
    # autoaccess new keys
    ssh.load_system_host_keys(os.path.expanduser(os.path.join("~",
                                                              ".ssh",
                                                              "known_hosts")))
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    #TODO: handle exceptions if connection does not work.
    # use private key if exists
    if os.path.exists(settings['PRIVATE_KEY']):
        privatekeyfile = os.path.expanduser(settings['PRIVATE_KEY'])
        mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
        ssh.connect(ip_address, username=settings['USER_NAME'], timeout=60, pkey=mykey)
    else:
        print("%s %s %s" % (ip_address, settings['USER_NAME'], settings['PASSWORD']))
        print(ssh)
        ssh.connect(ip_address, username=settings['USER_NAME'],
                    password=settings['PASSWORD'], timeout=60)

    #channel = ssh.invoke_shell().open_session()
    return ssh


def run_command(ssh, command, current_dir=None):
    logger.debug("%s %s " % (current_dir, command))
    if current_dir:
        command = "cd %s;%s" % (current_dir, command)
    logger.debug(command)
    stdin, stdout, stderr = ssh.exec_command(command)
    return stdout.readlines()


def run_sudo_command(ssh, command, settings, instance_id):
    chan = ssh.invoke_shell()
    chan.send('sudo -s\n')
    full_buff = ''
    buff = ''
    while not '[%s@%s ~]$ ' % (settings['USER_NAME'], instance_id) in buff:
        resp = chan.recv(9999)
        #logger.debug("resp=%s" % resp)
        buff += resp
    logger.debug("buff = %s" % buff)
    full_buff += buff

    chan.send("%s\n" % command)
    buff = ''
    while not '[root@%s %s]# ' % (instance_id, settings['USER_NAME']) in buff:
        resp = chan.recv(9999)
        #logger.debug("resp=%s" % resp)
        buff += resp
    logger.debug("buff = %s" % buff)
    full_buff += buff

    # TODO: handle stderr

    chan.send("exit\n")
    buff = ''
    while not '[%s@%s ~]$ ' % (settings['USER_NAME'], instance_id) in buff:
        resp = chan.recv(9999)
        #logger.debug("resp=%s" % resp)
        buff += resp
    logger.debug("3buff = %s" % buff)
    full_buff += buff

    chan.close()
    return (full_buff, '')


def install_deps(ssh, packages, settings, instance_id):
    for pack in packages:
        stdout, stderr = run_sudo_command(
            ssh, 'yum -y install %s' % pack,
            settings=settings, instance_id=instance_id)
        logger.debug("install stdout=%s" % stdout)
        logger.debug("install stderr=%s" % stderr)


def unpack(ssh, environ_dir, package_file):
    res = run_command(
        ssh, 'tar --directory=%s --extract --gunzip --verbose --file=%s'
        % (environ_dir, os.path.join(environ_dir, package_file)))
    logger.debug(res)


def compile(ssh, environ_dir, compile_file, package_dirname,
             compiler_command):
    run_command(ssh, "%s %s.f -o %s " % (compiler_command,
                                          compile_file,
                                          compile_file),
                 current_dir=os.path.join(environ_dir, package_dirname))


def mkdir(ssh, dir):
    run_command(ssh, "mkdir %s" % dir)


def get_file(ssh, source_path, package_file, environ_dir):
    ftp = ssh.open_sftp()
    logger.debug("%s %s %s" % (source_path, package_file, environ_dir))
    source_file = os.path.join(source_path, package_file).replace('\\', '/')
    dest_file = os.path.join(environ_dir, package_file).replace('\\', '/')
    logger.debug("%s %s" % (source_file, dest_file))
    try:
        ftp.get(source_file, dest_file)
    except IOError:
        logger.warning("%s not found" % package_file)


def put_file(ssh, source_path, package_file, environ_dir):
    ftp = ssh.open_sftp()
    logger.debug("%s %s" % (source_path, environ_dir))
    source_file = os.path.join(source_path, package_file).replace('\\', '/')
    dest_file = os.path.join(environ_dir, package_file).replace('\\', '/')
    logger.debug("%s %s" % (source_file, dest_file))
    ftp.put(source_file, dest_file)


def get_package_pid(ssh, command):
    pid = run_command(ssh, "/sbin/pidof %s" % command)
    if len(pid):
        pid = pid[0]  # if some returns, the pids are in first element
    return pid
