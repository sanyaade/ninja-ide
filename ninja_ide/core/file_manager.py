import os
import re
import threading
import shutil

from PyQt4 import QtCore

from ninja_ide.core import settings


#Lock to protect the file's writing operation
file_store_content_lock = threading.Lock()


class NinjaIOException(Exception):
    """
    IO operation's exception
    """
    pass


class NinjaFileExistsException(Exception):
    """
    Try to override existing file without confirmation exception.
    """

    def __init__(self, filename=''):
        Exception.__init__(self, 'The file already exists.')
        self.filename = filename


def create_init_file(folderName):
    """Create a __init__.py file in the folder received."""
    if not os.path.isdir(folderName):
        raise NinjaIOException("The destination folder does not exist")
    name = os.path.join(folderName, '__init__.py')
    if file_exists(name):
        raise NinjaFileExistsException(name)
    f = open(name, 'w')
    f.flush()
    f.close()


def create_init_file_complete(folderName):
    """Create a __init__.py file in the folder received.

    This __init__.py will contain the information of the files inside
    this folder."""
    if not os.path.isdir(folderName):
        raise NinjaIOException("The destination folder does not exist")
    patDef = re.compile('^def .+')
    patClass = re.compile('^class .+')
    patExt = re.compile('.+\\.py')
    files = os.listdir(folderName)
    files = filter(patExt.match, files)
    files.sort()
    imports_ = []
    for f in files:
        read = open(os.path.join(folderName, f), 'r')
        imp = [re.split('\\s|\\(', line)[1] for line in read.readlines()
                if patDef.match(line) or patClass.match(line)]
        imports_ += ['from ' + f[:-3] + ' import ' + i for i in imp]
    name = os.path.join(folderName, '__init__.py')
    fi = open(name, 'w')
    for import_ in imports_:
        fi.write(import_ + '\n')
    fi.flush()
    fi.close()


def create_folder(folderName):
    """Create a new Folder inside the one received as a param."""
    if os.path.exists(folderName):
        raise NinjaIOException("The folder already exist")
    os.mkdir(folderName)
    create_init_file(folderName)


def create_tree_folders(folderName):
    """Create a group of folders, one inside the other."""
    if os.path.exists(folderName):
        raise NinjaIOException("The folder already exist")
    os.makedirs(folderName)


def folder_exists(folderName):
    """Check if a folder already exists."""
    return os.path.isdir(folderName)


def file_exists(path, fileName=''):
    """Check if a file already exists."""
    if fileName != '':
        path = os.path.join(path, fileName)
    return os.path.isfile(path)


def _search_coding_line(txt):
    """Search a pattern like this: # -*- coding: utf-8 -*-."""
    coding_pattern = "coding[:=]\s*([-\w.]+)"
    pat_coding = re.search(coding_pattern, txt)
    if pat_coding:
        return pat_coding.groups()[0]
    return 'UTF-8'


def read_file_content(fileName):
    """Read a file content, this function is used to load Editor content."""
    if not os.path.exists(fileName):
        raise NinjaIOException("The file does not exist")
    if not os.path.isfile(fileName):
        raise NinjaIOException("%s is not a file" % fileName)
    f = QtCore.QFile(fileName)
    if not f.open(QtCore.QIODevice.ReadOnly | QtCore.QIODevice.Text):
        raise NinjaIOException("%s" % f.errorString())
    #QIODevice.Text convert \r\n to \n
    stream = QtCore.QTextStream(f)
    content = stream.readAll()
    encoding = _search_coding_line(content)
    if encoding:
        #reset the stream options
        stream.reset()
        stream.seek(0)
        #Set the specific encoding
        stream.setCodec(encoding)
        content = stream.readAll()
    f.close()
    return unicode(content)


def get_basename(fileName):
    """Get the name of a file or folder specified in a path."""
    return os.path.basename(fileName)


def get_folder(fileName):
    """Get the name of the folder containing the file or folder received."""
    return os.path.dirname(fileName)


def _real_store_file_content(fileName, content):
    """Function that actually save the content of a file (thread)."""
    global file_store_content_lock
    file_store_content_lock.acquire()
    try:
        f = QtCore.QFile(fileName)
        if not f.open(QtCore.QIODevice.WriteOnly | QtCore.QIODevice.Truncate):
            raise NinjaIOException(f.errorString())
        #QTextStream detect locales ;)
        stream = QtCore.QTextStream(f)
        encoding = _search_coding_line(content)
        if encoding:
            stream.setCodec(encoding)
        encoded_stream = stream.codec().fromUnicode(content)
        f.write(encoded_stream)
        f.flush()
        f.close()
    except:
        raise
    finally:
        file_store_content_lock.release()


def store_file_content(fileName, content, addExtension=True, newFile=False):
    """Save content on disk with the given file name."""
    if fileName == '':
        raise Exception()
    ext = (os.path.splitext(fileName)[-1])[1:]
    if ext == '' and addExtension:
        fileName += '.py'
    if newFile and file_exists(fileName):
        raise NinjaFileExistsException(fileName)
    t = threading.Thread(target=_real_store_file_content,
                            args=(fileName, content))
    t.start()
    #wait until the saver finish
    t.join()
    return fileName


def open_project(path):
    """Return a dict structure containing the info inside a folder."""
    if not os.path.exists(path):
        raise NinjaIOException("The folder already exist")
    d = {}
    for root, dirs, files in os.walk(path):
        d[root] = [[f for f in files
                if (os.path.splitext(f.lower())[-1]) in \
                settings.SUPPORTED_EXTENSIONS],
                dirs]
    return d


def open_project_with_extensions(path, extensions):
    """Return a dict structure containing the info inside a folder.

    This function uses the extensions specified by each project."""
    if not os.path.exists(path):
        raise NinjaIOException("The folder does not exist")
    d = {}
    for root, dirs, files in os.walk(path):
        d[root] = [[f for f in files
                if (os.path.splitext(f.lower())[-1]) in extensions],
                dirs]
    return d


def delete_file(path, fileName=None):
    """Delete the proper file.

    If fileName is None, path and fileName are joined to create the
    complete path, otherwise path is used to delete the file."""
    if fileName:
        path = os.path.join(path, fileName)
    if os.path.isfile(path):
        os.remove(path)


def delete_folder(path, fileName=None):
    """Delete the proper folder."""
    if fileName:
        path = os.path.join(path, fileName)
    if os.path.isdir(path):
        shutil.rmtree(path)


def rename_file(old, new):
    """Rename a file, changing its name from 'old' to 'new'."""
    if os.path.isfile(old):
        ext = (os.path.splitext(new)[-1])[1:]
        if ext == '':
            new += '.py'
        if file_exists(new):
            raise NinjaFileExistsException(new)
        os.rename(old, new)
        return new
    return ''


def get_file_extension(fileName):
    """Get the file extension in the form of: 'py'"""
    return os.path.splitext(fileName.lower())[-1][1:]


def get_module_name(fileName):
    """Get the name of the file without the extension."""
    module = os.path.basename(fileName)
    return (os.path.splitext(module)[0])


def convert_to_relative(basePath, fileName):
    """Convert a absolut path to relative based on its start with basePath."""
    if fileName.startswith(basePath):
        fileName = fileName.replace(basePath, '')
        if fileName.startswith(os.path.sep):
            fileName = fileName[1:]
    return fileName


def create_path(*args):
    """Join the paths provided in order to create an absolut path."""
    return os.path.join(*args)


def belongs_to_folder(path, fileName):
    """Determine if fileName is located under path structure."""
    return fileName.startswith(path)


def get_last_modification(fileName):
    """Get the last time the file was modified."""
    return QtCore.QFileInfo(fileName).lastModified()


def has_write_permission(fileName):
    """Check if the file has writing permissions."""
    return os.access(fileName, os.W_OK)


def check_for_external_modification(fileName, old_mtime):
    """Check if the file was modified outside ninja."""
    new_modification_time = get_last_modification(fileName)
    #check the file mtime attribute calling os.stat()
    if new_modification_time > old_mtime:
        return True
    return  False


def get_files_from_folder(folder, ext):
    """Get the files in folder with the specified extension."""
    filesExt = os.listdir(folder)
    filesExt = [f for f in filesExt if f.endswith(ext)]
    return filesExt
