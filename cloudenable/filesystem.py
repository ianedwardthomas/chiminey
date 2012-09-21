import os
import time

from fs.osfs import OSFS
import shutil
import tempfile

import logging
import logging.config

logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)


class FileSystem(object):
    def __init__(self, global_filesystem):
        self._create_global_filesystem(global_filesystem)
       
    def __init__(self, global_filesystem, local_filesystem):
        self._create_global_filesystem(global_filesystem)        
        if self.connector_fs.exists(local_filesystem):
            logger.error("Local filesystem '%s' already exists under '%s'" % (local_filesystem, global_filesystem))
        else:
            self.connector_fs.makedir(local_filesystem)
            logger.info("Local filesystem '%s' CREATED under '%s' " % (local_filesystem, global_filesystem))
    
    def _create_global_filesystem(self, global_filesystem):
        self.global_filesystem = global_filesystem
        self.connector_fs = OSFS(global_filesystem, create=True)
        logger.info("Global filesystem '%s' CREATED " % global_filesystem)
    
    def create(self, local_filesystem, file_element):
        if not self.connector_fs.exists(local_filesystem):
            logger.error("Destination filesystem '%s' does not exist" % local_filesystem)
            return False
    
        destination_file_name = self.global_filesystem + "/" + local_filesystem + "/" + file_element.name
        destination_file = open(destination_file_name, 'w')
        destination_file.write(file_element.content)
        destination_file.close()
        logger.info("File '%s' CREATED" % (destination_file_name))
        return True
        
        
    def retrieve(self, path):
        # check for missing path# MUST RETURN filesystem
        pass
    def delete(self, path):
        pass
    
    def update(self, path, felem):
        source_file = path + "/" + felem.name
        f = FileElement(felem.name)
        for (i,content) in enumerate(felem.get(contents)):
            l = felem.retrieve(i)
            f.append(l)
        file = _copy_contents_to_file(f)
        shui.copy(file, dest_filesystem)
    
    def _copy_contents_to_file(self, file_element, new_file_destination):
        temp_file = tempfile.NamedTemporaryFile(delete=False,mode='w')   
        #os.chmod(temp_file.name, 0777)
        print "contents", file_element.contents
        file = open(new_file_destination, 'w')
        for content in file_element.contents:
            print content
            temp_file.write("Iman \n" )
            file.write(content+"\n")
            
        print temp_file.name
        print new_file_destination
        #shutil.copyfile(temp_file.name, new_file_destination)
        #temp_file.close()
        
        return True
    

class FileElement(object):
    # Assume that whole file is contained in one big string
    # as it makes json parsing easier

    def __init__(self, name):
        self.name = name
        self.content = ""

    def create(self,content):
        self.content = content

    def retrieve(self):
        return self.content



'''class FileElement(object):
    
    # lines = array of string
    
    # lines = File
    def __init__(self,name):
        self.name = name
        
    def create(self, lines):
        self.lines = lines
        
    def retrieve(self):
        return self.lines
    
    def retrieve(self, line_no):
        return self.lines[line_no]
    
    def append_line(self, line):
        self.lines.append(line)
'''
    
def mainloop():
    global_filesystem = '/home/iyusuf/connect'
    local_filesystem = 'a'
    fsys = FileSystem(global_filesystem, local_filesystem)
        
    f1 = FileElement("c")
    contents = "hello\n" + "iman\n" +"seid\n"+"osman\n"
    f1.create(contents)
    fsys.create(local_filesystem, f1)
        
    #    fsys.update("a/b",f2) #whole repace

     #   fsys.update("a/b/d",f2)
        
      #  fsys.delete("a/b/c")
        



if __name__ == '__main__':
    begins = time.time()
    mainloop()
    ends = time.time()
    print "Total execution time: %d seconds" % (ends-begins)
    