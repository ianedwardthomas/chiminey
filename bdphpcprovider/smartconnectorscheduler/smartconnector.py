from bdphpcprovider.smartconnectorscheduler import models
from urlparse import urlparse
import time
import os
import utility
import logging
logger = logging.getLogger(__name__)
#Every stage may be thrown away after completion


class Error(Exception):
    pass


class PackageFailedError(Error):
    pass


# This stage has no impact on other stages
class Stage(object):
    def __init__(self):
        pass

    def triggered(self, context):
        """
        Return true if the directory pattern triggers this stage, or there
        has been any other error
        """
        # FIXME: Need to verify that triggered is idempotent.
        return True

    def process(self, context):
        """ perfrom the stage operation
        """
        pass

    def output(self, context):
        """ produce the resulting datfiles and metadata
        """
        pass

    def get_url_with_pkey(self, settings, url_or_relative_path,
                          is_relative_path=False, ip_address='127.0.0.1'):
        '''
         This method appends private key, username, passowrd and/or rootpath
         parameters at end of a url. If only relative path is passed,
         a url is constructed based on the data @url_or_relative_path and
         @settings.

        Suppose
            url_or_relative_path = 'nectar@new_payload'
            is_relative_path = True
            ip_address = 127.0.0.1
            root_path = /home/centos
        the platform is nectar and the relative path is new_payload
        The new url will be ssh://127.0.0.1/new_payload?root_path=/home/centos

        :param settings:
        :param url_or_relative_path:
        :param is_relative_path:
        :param ip_address:
        :return:
        '''
        username = settings['USER_NAME']
        password = settings['PASSWORD']
        private_key = ''

        if is_relative_path:
            url = 'http://' + url_or_relative_path
        else:
            url = url_or_relative_path
        parsed_url = urlparse(url)
        platform = parsed_url.username
        if platform == 'nectar':
            private_key = settings['PRIVATE_KEY_NECTAR']
            scheme = 'ssh'
        elif platform == 'nci':
            private_key = settings['PRIVATE_KEY_NCI']
            scheme = 'ssh'
        else:
            scheme = urlparse(url).scheme
            if scheme == 'file':
                platform = 'local'
            else:
                logger.debug("scheme [%s] unknown \n"
                             "Valid schemes [file, ssh]" % scheme)
                #raise NotImplementedError()
                return
        platform_object = models.Platform.objects.get(name=platform)
        root_path = platform_object.root_path
        if is_relative_path:
            partial_path = parsed_url.path
            if partial_path:
                if partial_path[0] == os.path.sep:
                    partial_path = parsed_url.path[1:]
            relative_path = os.path.join(parsed_url.hostname, partial_path)
            logger.debug('host=%s path=%s relativepath=%s' % (parsed_url.hostname,
                                                              partial_path,
                                                              relative_path))
            url_with_pkey = '%s://%s/%s?key_filename=%s' \
                            '&username=%s&password=%s' \
                            '&root_path=%s' % (scheme, ip_address,
                                               relative_path, private_key,
                                               username, password, root_path)
        else:
            url_with_pkey = url_or_relative_path + \
                            '?key_filename=%s&username=%s' \
                            '&password=%s&root_path=%s' % (private_key,
                                                           username, password,
                                                           root_path)
        logger.debug("Destination %s url_pkey %s" % (str(is_relative_path), url_with_pkey))
        return  url_with_pkey


class UI(object):
    pass


class Configure(Stage, UI):
    """
        - Load config.sys file into the filesystem
        - Nothing beyond specifying the path to config.sys
        - Later could be dialogue box,...

    """
    def triggered(self, context):
        #check for filesystem in context
        return True

        #logger.debug("%s" % field_val)
    def process(self, context):
        # - Load config.sys file into the filesystem
        # - Nothing beyond specifying the path to config.sys
        # - Later could be dialogue box,...
        # 1. creates instance of file system
        # 2. pass the file system as entry in the Context
        # create status  file in file system
        #print " Security Group", filesystem.settings.SECURITY_GROUP

        pass

    # indicate the process() is completed
    def output(self, context):
        # store in filesystem
        pass


class Create(Stage):
    def triggered(self, context):
        """ return true if the directory pattern triggers this stage
        """
        #check the context for existence of a file system or other
        # key words, then if true, trigger
        #self.metadata = self._load_metadata_file()

        if True:
            self.settings = utility.load_generic_settings()
            return True

    def _transform_the_filesystem(filesystem, settings):
        key = settings['ec2_access_key']
        print key

    def process(self, context):

        # get the input from the user to override config settings
        # load up the metadata

        #settings = {}
        #settings['number_vm_instances'] = self.metadata.number

        #settings['ec2_access_key'] = self.metadata.ec2_access_key
        #settings['ec2_secret_key'] = self.metadata.ec2_secret_key
        # ...

        #self.temp_sys = FileSystem(filesystem)

        #self._transform_the_filesystem(self.temp_sys, settings)

        #import codecs
        #f = codecs.open('metadata.json', encoding='utf-8')
        #import json
        #metadata = json.loads(f.read())
        print "Security Group ", self.settings.SECURITY_GROUP
        pass

    def output(self, context):
        # store in filesystem
        #self._store(self.temp_sys, filesystem)
        pass


class Setup(Stage):

    def triggered(self, context):
        pass

    def process(self, context):
        pass

    def output(self, context):
        pass


class Run(Stage):
    #json output
    def triggered(self, context):
        pass

    def process(self, context):
        pass

    def output(self, context):
        pass


class Check(Stage):
    def triggered(self, context):
        pass

    def process(self, context):
        pass

    def output(self, context):
        pass


class Teardown(Stage):
    def triggered(self, context):
        pass

    def process(self, context):
        pass

    def output(self, context):
        pass


class ParallelStage(Stage):
    def triggered(self, context):
        return True

    def process(self, context):

        while(True):
            done = 0
            for stage in smart_con.stages:
                print "Working in stage", stage
                if stage.triggered(context):
                    stage.process(context)
                    stage.output(context)
                    done += 1
                    #smart_con.unregister(stage)
                    #print "Deleting stage",stage
                    print done
            if done == len(smart_con.stages):
                break

        while s.triggered(context):
            s.process(context)
            s.output(context)
            print context

    def output(self, context):
        pass


class GridParameterStage(Stage):
    pass


class SequentialStage(Stage):

    def __init__(self, stages):
        self.stages = stages

    def triggered(self, context):
        return True

    def process(self, context):
        for stage in self.stages:
            if stage.triggered(context):
                stage.process(context)
                stage.output(context)

    def output(self, context):
        pass


class SmartConnector(object):
    """ A smart Connector is a container for stages """

    def __init__(self, stage=None):
        self.stages = []
        if stage:
            self.stages.append(stage)

    def register(self, stage):
        self.stages.append(stage)

    def process(self, context):
        if self.stage.triggered(context):
            self.stage.process(context)
            self.stage.output(context)
        else:
            raise PackageFailedError()


def mainloop():
# load system wide settings, e.g Security_Group
#communicating between stages: crud context or filesystem
#build context with file system as its only entry
    context = {}
    context['version'] = "1.0.0"

    #smart_con = SmartConnector()
    filesys = FileSystem()
    path_fs = '/home/iyusuf/connectorFS'
    filesys.create_initial_filesystem(path_fs)
   # filesys.create_file(path_fs, 'Iman')
    filesys.create_filesystem("newFS")

    filesys.delete_filesystem("newFS")
    filesys.delete_file("Iman")
    filesys.create_file('/home/iyusuf/Butini',
                        dest_filesystem='/home/iyusuf/connectorFS/Seid')

    file_name = 'tobeupdated'
    absolute_path = os.path.join(filesys.toplevel_filesystem,
                                 file_name)

    f = open(absolute_path, 'w')
    f.write("Line 1")
    f.write("line 2")
    f.close()


    #filesys.update_file('Butini')
    #filesys.delete_file(path_fs, 'Iman')

    #filesys.create_initial_filesystem()
    #filesys.load_generic_settings()

    #for stage in (Configure(), Create(), Setup(), Run(), Check(), Teardown()):
     #   smart_con.register(stage)


    #print smart_con.stages

    #while loop is infinite:
    # check the semantics for 'dropping data' into
    # designated location.
    #What happens if data is dropped while
    #another is in progress?


    #while(True):

    #while (True):
     #   done = 0
      #  for stage in smart_con.stages:
       #     print "Working in stage",stage
        #    if stage.triggered(context):
         #       stage.process(context)
          #      stage.output(context)
           #     done += 1
                #smart_con.unregister(stage)
                #print "Deleting stage",stage
            #    print done

        #if done == len(smart_con.stages):
         #   break

if __name__ == '__main__':
    begins = time.time()
    mainloop()
    ends = time.time()
    print "Total execution time: %d seconds" % (ends - begins)
