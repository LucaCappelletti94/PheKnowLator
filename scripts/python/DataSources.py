#!/usr/bin/env python
# -*- coding: utf-8 -*-


# import needed libraries
import datetime
import gzip
import io
import os.path
import requests
import shutil
import urllib.request as request

from abc import ABCMeta, abstractmethod
from contextlib import closing
from owlready2 import subprocess
from tqdm import tqdm


class DataSource(object):
    """The class takes an input string that contains the file path/name of a text file listing different data sources.
    Each source is shown as a URL.

    The class initiates the downloading of different data sources and generates a metadata file that contains
    important information on each of the files that is downloaded.

    The class has two subclasses which inherit its methods. Each subclass contains an altered version of the primary
    classes methods that are specialized for that specific data type.

    Attributes:
        data_path (str): A string file path/name to a text file storing URLs of different sources to download.
        data_type (str): A string specifying the type of data source.
        source_list (list): A list of URLs containing the data sources to download/process.
        data_files (list): A list of strings, which contain the full file path/name of each downloaded data source.
        metadata (list): An empty list that will be used to store metadata information for each downloaded resource.
    """

    __metaclass__ = ABCMeta

    def __init__(self, data_path):
        self.data_path = data_path
        self.data_type = data_path.split('/')[-1].split('.')[0]
        self.source_list = {}
        self.data_files = {}
        self.metadata = []

    def parses_resource_file(self):
        """Verifies a file contains data and then outputs a list where each item is a line from the input text file.

        Returns:
            source_list (dict): A dictionary, where the key is the type of data and the value is the file path or url.

        Raises:
            An exception is raised if the input file is empty.
        """

        print('\n' + '=' * 100)
        print('Checking file containing data resources')
        print('=' * 100 + '\n')

        if os.stat(self.data_path).st_size == 0:
            raise Exception('ERROR: input file: {} is empty'.format(self.data_path))

        else:
            self.source_list = {row.strip().split(',')[0]: row.strip().split(',')[1].strip() for row in open(
                                self.data_path).read().split('\n')}

    def downloads_data_from_url(self, download_type):
        """Downloads each source from a list and writes the downloaded file to a directory.

        Args:
            download_type (str): A string that indicates whether or not the ontologies should be downloaded
                                with imported ontologies ('imports').
        """

        pass

    def generates_source_metadata(self):
        """Extracts and stores metadata for imported data sources. Metadata includes the date of download,
        date of last modification to the file, the difference in days between last date of modification and current
        download date, file size in bytes, path to file, and URL from which the file was downloaded for each data source

        Returns:
            metadata (list): A nested list, where first item is today's date and each remaining item is a list that
                            contains metadata information for each downloaded data source.
        """

        print('\n' + '=' * 100)
        print('Generating Metadata')
        print('=' * 100 + '\n')

        self.metadata.append(['#' + str(datetime.datetime.utcnow().strftime('%a %b %d %X UTC %Y')) + ' \n'])

        for i in tqdm(self.data_files.keys()):
            source = self.data_files[i]

            # get vars for metadata file
            try:
                file_info = requests.head(self.source_list[i])

                if 'modified' in [x.lower() for x in file_info.headers.keys()]:
                    mod_info = file_info.headers['modified'][0]

                elif 'Last-Modified' in [x.lower() for x in file_info.headers.keys()]:
                    mod_info = file_info.headers['Last-Modified'][0]

                elif 'Date' in [x.lower() for x in file_info.headers.keys()]:
                    mod_info = file_info.headers['Date']

                else:
                    mod_info = datetime.datetime.now().strftime('%a, %d %b %Y %X GMT')

            # for ftp downloads that don't have header info
            except requests.exceptions.InvalidSchema:
                mod_info = datetime.datetime.now().strftime('%a, %d %b %Y %X GMT')

            # reformat date
            mod_date = datetime.datetime.strptime(mod_info, '%a, %d %b %Y %X GMT').strftime('%m/%d/%Y')
            diff_date = (datetime.datetime.now() - datetime.datetime.strptime(mod_date, '%m/%d/%Y')).days

            # add metadata for each source as nested list
            source_metadata = ['DOWNLOAD_URL= {}'.format(str(self.source_list[i])),
                               'DOWNLOAD_DATE= {}'.format(str(datetime.datetime.now().strftime('%m/%d/%Y'))),
                               'FILE_SIZE_IN_BYTES= {}'.format(str(os.stat(self.data_files[i]).st_size)),
                               'FILE_AGE_IN_DAYS= {}'.format(str(diff_date)),
                               'DOWNLOADED_FILE_LOCATION= {}'.format(str(source)),
                               'FILE_LAST_MOD_DATE= {}'.format(str(mod_date))]

            self.metadata.append(source_metadata)

        return self.metadata

    def writes_source_metadata_locally(self):
        """Generates a text file that stores metadata for the data sources that it imports.

        Returns:
            None.
        """

        print('\n' + '=' * 100)
        print('Writes Metadata File to local repository')
        print('=' * 100 + '\n')

        # open file to write to and specify output location
        write_loc_part1 = str('/'.join(list(self.data_files.values())[1].split('/')[:-1]) + '/')
        write_loc_part2 = str('_'.join(self.data_type.split('_')[:-1]))
        write_location = write_loc_part1 + write_loc_part2 + '_metadata.txt'

        # open file to write data
        outfile = open(write_location, 'w')
        outfile.write(self.metadata[0][0])
        print('Writing ' + str(self.data_type) + ' metadata \n')

        # write data
        for i in tqdm(range(1, len(self.data_files.keys()))):
            source = self.metadata[i]

            outfile.write(str(source[0]) + '\n')
            outfile.write(str(source[1]) + '\n')
            outfile.write(str(source[2]) + '\n')
            outfile.write(str(source[3]) + '\n')
            outfile.write(str(source[4]) + '\n')
            outfile.write(str(source[5]) + '\n')
            outfile.write('\n')

        outfile.close()

        return None

    @abstractmethod
    def gets_data_type(self):
        """"A string representing the type of data being processed."""

        pass


class OntData(DataSource):

    def gets_data_type(self):
        """"A string representing the type of data being processed."""

        return 'Ontology Data'

    def parses_resource_file(self):
        """Parses data from a file and outputs a list where each item is a line from the input text file.

        Returns:
            source_list (list): A list, where each item represents a data source from the input text file.

        Raises:
            An exception is raised if the file contains data.
            An exception is raised if a URL does point to a source containing data.
        """

        print('\n' + '=' * 100)
        print('Checking file containing data resources')
        print('=' * 100 + '\n')

        # CHECK - file has data
        if os.stat(self.data_path).st_size == 0:
            raise Exception('ERROR: input file: {} is empty'.format(self.data_path))

        else:
            source_list = {row.strip().split(',')[0]: row.strip().split(',')[1].strip() for row in open(
                           self.data_path).read().split('\n')}

            # CHECK
            valid_sources = [url for url in source_list.values() if 'purl.obolibrary.org/obo' in url or 'owl' in url]

            if len(source_list) == len(valid_sources):
                self.source_list = source_list

            else:
                raise Exception('ERROR: Not all URLs were formatted properly')

    def downloads_data_from_url(self, download_type):
        """Takes a string representing a file path/name to a text file as an argument. The function assumes
        that each item in the input file list is an URL to an OWL/OBO ontology.

        For each URL, the referenced ontology is downloaded, and used as input to an OWLTools command line argument (
        https://github.com/owlcollab/owltools/wiki/Extract-Properties-Command), which facilitates the downloading of
        ontologies that are imported by the primary ontology. The function will save the downloaded ontology + imported
        ontologies.

        Args:
            download_type (str): A string that is used to indicate whether or not the ontologies should be downloaded
                                 with imported ontologies ('imports').

        Returns:
            source_list (list): A list, where each item in the list represents an ontology via URL.

        Raises:
            An exception is raised if any of the URLs passed as command line arguments fails to return data.
        """

        # set location where to write data
        file_loc = './' + str(self.data_path.split('/')[:-1][0]) + '/ontologies/'

        print('\n' + '=' * 100)
        print('Downloading Ontology Data: {0} to "{1}"'.format(self.data_type, file_loc))
        print('=' * 100 + '\n')

        # process data
        for i in tqdm(self.source_list.keys()):
            source = self.source_list[i]
            file_prefix = source.split('/')[-1].split('.')[0]
            print('\n' + 'Downloading: {}'.format(str(file_prefix)) + '\n')

            if download_type == 'imports' and 'purl' in source:
                try:
                    subprocess.check_call(['./resources/lib/owltools',
                                           str(source),
                                           '--merge-import-closure',
                                           '-o',
                                           './resources/ontologies/'
                                           + str(file_prefix) + '_with_imports.owl'])

                    self.data_files[i] = './resources/ontologies/' + str(file_prefix) + '_with_imports.owl'

                except subprocess.CalledProcessError as error:
                    print(error.output)

            elif download_type != 'imports' and 'purl' in source:
                try:
                    subprocess.check_call(['./resources/lib/owltools',
                                           str(source),
                                           '-o',
                                           './resources/ontologies/'
                                           + str(file_prefix) + '_without_imports.owl'])

                    self.data_files[i] = './resources/ontologies/' + str(file_prefix) + '_without_imports.owl'

                except subprocess.CalledProcessError as error:
                    print(error.output)

            else:
                filename = './resources/ontologies/' + str(file_prefix) + '.owl'

                with closing(request.urlopen(source)) as r:
                    with open(filename, 'wb') as f:
                        shutil.copyfileobj(r, f)

                self.data_files[i] = './resources/ontologies/' + str(file_prefix) + '.owl'

        # CHECK
        if len(self.source_list) != len(self.data_files):
            raise Exception('ERROR: Not all URLs returned a data file')


class Data(DataSource):

    def gets_data_type(self):
        """"A string representing the type of data being processed."""

        return 'Edge Data'

    def downloads_data_from_url(self, download_type):
        """Takes a string representing a file path/name to a text file as an argument. The function assumes that
        each item in the input file list is a valid URL.

        Args:
            download_type (str): A string that is used to indicate whether or not the ontologies should be downloaded
                                 with imported ontologies ('imports'). Within this subclass, this argument is
                                 currently ignored.

        Returns:
            source_list (list): A list, where each item in the list represents a data source.

        Raises:
            An exception is raised if any URL does point to a valid endpoint containing data.
        """

        # set location where to write data
        file_loc = './' + str(self.data_path.split('/')[:-1][0]) + '/edge_data/'

        print('\n' + '=' * 100)
        print('Downloading Ontology Data: {0} to "{1}"'.format(self.data_type, file_loc))
        print('=' * 100 + '\n')

        for i in tqdm(self.source_list.keys()):
            source = self.source_list[i]
            file_prefix = source.split('/')[-1].split('.')[0]
            print('\n')
            print('Downloading: {edge} - {source}\n'.format(edge=i, source=file_prefix))

            file_name = input('Enter file name (i.e. chemical-gene_ctd_class_evidence.txt): ')
            self.data_files[i] = './resources/edge_data/' + file_name

            # verify endpoint and download data -- checks whether downloaded data is compressed
            if '.gz' in source:
                response = requests.get(source)
                content = gzip.GzipFile(fileobj=io.BytesIO(response.content)).read()
            else:
                response = requests.get(source)
                content = io.BytesIO(response.content).read()

            # write downloaded file to directory
            file = open('./resources/edge_data/' + file_name, 'w')
            file.write(str(content))
            file.close()

        # CHECK
        if len(self.source_list) != len(self.data_files):
            raise Exception('ERROR: Not all URLs returned a data file')
